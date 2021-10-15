from json.encoder import JSONEncoder
import re
from typing import Dict, List, Any, TypeVar
import os
import json
from dataclasses import dataclass

import bpy
from bpy.types import Mask

T = TypeVar("T")

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
    UV1: Textures = Textures(
        ["Trunk_BaseColor", "Diffuse", "DiffuseTexture", "Base_Color_Tex", "Tex_Color"],
        ["Trunk_Normal", "Normals", "Normal", "Base_Normal_Tex", "Tex_Normal"],
        ["Trunk_Specular", "SpecularMasks"],
        ["EmissiveTexture"],
        ["MaskTexture"]
    )
    UV2: Textures = Textures(
        ["Diffuse_Texture_2"],
        ["Normals_Texture_2"],
        ["Specular_Texture_2"],
        ["Emissive_Texture_2"],
        ["MaskTexture_2"]
    )
    UV3: Textures = Textures(
        ["Diffuse_Texture_3"],
        ["Normals_Texture_3"],
        ["Specular_Texture_3"],
        ["Emissive_Texture_3"],
        ["MaskTexture_3"]
    )
    UV4: Textures = Textures(
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

class MyEncoder(JSONEncoder):
        def default(self, o):
            return o.to_dict()

def aeskeys_from_list(x: Any) -> List[T]:
    l = []
    l.append({
        "Guid": "00000000000000000000000000000000",
        "Key": bpy.context.scene.aeskey
    })
    for a in x:
        if a.pakname == "" and a.daeskey == "":
            continue
        if a.guid == "" and a.pakname == "":
            continue
        if a.daeskey == "":
            continue

        d = {}
        if a.guid != "":
            d["Guid"] = a.guid
        if a.pakname != "":
            d["FileName"] = a.pakname
        d["Key"] = a.daeskey
        l.append(d)
    return l

def textures_to_mapping(context: bpy.context) ->TextureMapping:    
    temp_map = TextureMapping()
    for i in range(1, 5): # 4UVs
        for t in ["Diffuse", "Normal", "Specular", "Emission", "Mask"]:
            textures = getattr(context, f"{t}_{i}".lower(), "").split(",")
            textures = [x.strip() for x in textures]
            if len(t) != 0 and textures != ['']:
                setattr(getattr(temp_map, f"UV{i}"), t, textures) # basically temp_map.UV{i}.{Texture} = textures
    return temp_map

class Config:
    Documentation: str = "https://github.com/Amrsatrio/BlenderUmap/blob/master/README.md"
    PaksDirectory: str
    ExportPath: str
    UEVersion: str
    EncryptionKeys: List[Any]
    bDumpAssets: bool
    ObjectCacheSize: int
    bReadMaterials: bool
    bExportToDDSWhenPossible: bool
    bExportBuildingFoundations: bool    
    ExportPackage: str

    def __init__(self) -> None:
        sc = bpy.context.scene
        self.PaksDirectory = sc.Game_Path[:-1]
        self.ExportPath = sc.exportPath
        self.bUseCustomEngineVer = sc.bUseCustomEngineVer
        self.CustomVersion = sc.customEngineVer
        self.UEVersion = sc.ue4_versions
        self.EncryptionKeys = sc.dpklist
        self.bDumpAssets = sc.bdumpassets
        self.ObjectCacheSize = sc.ObjectCacheSize
        self.bReadMaterials = sc.readmats
        self.bExportToDDSWhenPossible = sc.bExportToDDSWhenPossible
        self.bExportBuildingFoundations = sc.bExportBuildingFoundations
        self.ExportPackage = sc.package
        self.Textures = textures_to_mapping(sc)

    def to_dict(self) -> dict:
        result: dict = {"_Documentation": self.Documentation,
                        "PaksDirectory": self.PaksDirectory,
                        "ExportPath": self.ExportPath,
                        "UEVersion": self.CustomVersion if self.bUseCustomEngineVer else self.UEVersion,
                        "bDumpAssets": self.bDumpAssets, "ObjectCacheSize": self.ObjectCacheSize,
                        "bReadMaterials": self.bReadMaterials,
                        "bExportToDDSWhenPossible": self.bExportToDDSWhenPossible,
                        "bExportBuildingFoundations": self.bExportBuildingFoundations,
                        "ExportPackage": self.ExportPackage,
                        "EncryptionKeys": aeskeys_from_list(self.EncryptionKeys),
                        "Textures": textures_to_mapping(bpy.context.scene).to_dict()
                        }
        return result

    def load(self, out=None): #TODO: load textures
        if not os.path.exists(os.path.join(self.ExportPath, "config.json")):
            return
        with open(os.path.join(self.ExportPath, "config.json"), "r") as f:
            data = json.load(f)
            if out is None:
                out = data

        sc = bpy.context.scene

        sc.Game_Path = data["PaksDirectory"] + "/"
        sc.exportPath = data.get("ExportPath") or self.ExportPath

        version = data["UEVersion"]
        if re.search(r"(game_ue\d_\d+)", version, re.IGNORECASE):
            sc.ue4_versions = version
        else:
            sc.bUseCustomEngineVer = True
            sc.customEngineVer = version

        sc.bdumpassets = data["bDumpAssets"]
        sc.ObjectCacheSize = data["ObjectCacheSize"]
        sc.readmats = data["bReadMaterials"]
        sc.bExportToDDSWhenPossible = data["bExportToDDSWhenPossible"]
        sc.bExportBuildingFoundations = data["bExportBuildingFoundations"]
        sc.package = data["ExportPackage"]

        for a in range(len(sc.dpklist)):
            sc.dpklist.remove(a)

        sc.list_index = 0
        i = 0
        for x in data["EncryptionKeys"]:
            if guid := x.get("Guid"):
                if guid == "00000000000000000000000000000000":
                    sc.aeskey = x["Key"]
                    continue

            sc.list_index = i
            sc.dpklist.add()
            dpk = sc.dpklist[i]
            dpk.guid = x.get("Guid") or ""
            dpk.pakname = x.get("FileName") or ""
            dpk.daeskey = x["Key"]
            i += 1

        # load textures
        for i in range(1, 5):
            for t in ["Diffuse", "Normal", "Specular", "Emission", "Mask"]:
                textures = data["Textures"]["UV" + str(i)][t if t != "Mask" else "MaskTexture"]
                setattr(sc, f"{t}_{i}".lower(), ",".join(textures))

    def dump(self, path):
        with open(os.path.join(path, "config.json"), "w") as f:
            json.dump(self.to_dict(), f, indent=4, cls=MyEncoder)
