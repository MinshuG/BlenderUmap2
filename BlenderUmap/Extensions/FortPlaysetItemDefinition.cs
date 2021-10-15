using System;
using System.Collections.Generic;
using System.IO;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Objects;
using CUE4Parse.UE4.Objects.Core.Math;
using CUE4Parse.UE4.Objects.Core.Misc;
using CUE4Parse.UE4.Objects.Engine;
using CUE4Parse.UE4.Objects.UObject;
using CUE4Parse.Utils;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Serilog;

namespace BlenderUmap.Extensions {
    public static class FortPlaysetItemDefinition { // TODO: OverrideMaterials Support
        public static void ExportAndProduceProcessed(UObject obj) {
            var comps = new JArray();
            foreach (var actor in obj.GetOrDefault<FStructFallback[]>("PreviewActorData")) {
                var comp = new JArray();
                var ac = actor.GetOrDefault<UObject>("ActorClass");
                if (ac == null) continue;

                comps.Add(comp);
                comp.Add(Guid.NewGuid().ToString().Replace("-", ""));
                comp.Add(ac.Name.SubstringBefore("_C"));

                UObject staticMeshComp = new UObject();
                var mesh = new FPackageIndex();
                if (ac is UBlueprintGeneratedClass actorBlueprint) {
                    var mactor = actorBlueprint.ClassDefaultObject.Load(); 
                    mesh = mactor?.GetOrDefault<FPackageIndex>("StaticMesh");
                    staticMeshComp = mactor?.GetOrDefault<UObject>("StaticMeshComponent");
                }

                var matsObj = new JObject(); // matpath: [4x[str]]
                var textureDataArr = new JArray();
                var materials = new List<Program.Mat>();
                Program.ExportMesh(mesh, materials);
                
                if (Program.config.bReadMaterials) {
                    var material = actor.GetOrDefault<FPackageIndex>("BaseMaterial"); // /Script/FortniteGame.BuildingSMActor:BaseMaterial
                    var overrideMaterials = staticMeshComp?.GetOrDefault<List<FPackageIndex>>("OverrideMaterials"); // /Script/Engine.MeshComponent:OverrideMaterials

                    foreach (var textureDataIdx in actor.GetProps<FPackageIndex>("TextureData")) { // /Script/FortniteGame.BuildingSMActor:TextureData
                        var td = textureDataIdx?.Load();
                    
                        if (td != null) {
                            var textures = new JArray();
                            Program.AddToArray(textures, td.GetOrDefault<FPackageIndex>("Diffuse"));
                            Program.AddToArray(textures, td.GetOrDefault<FPackageIndex>("Normal"));
                            Program.AddToArray(textures, td.GetOrDefault<FPackageIndex>("Specular"));
                            textureDataArr.Add(new JArray { Program.PackageIndexToDirPath(textureDataIdx), textures });
                            var overrideMaterial = td.GetOrDefault<FPackageIndex>("OverrideMaterial");
                            if (overrideMaterial != null) {
                                material = overrideMaterial;
                            }
                        } else {
                            textureDataArr.Add(JValue.CreateNull());
                        }
                    }

                    for (int i = 0; i < materials.Count; i++) {
                        var mat = materials[i];
                        if (material != null) {
                            mat.Material = overrideMaterials != null && i < overrideMaterials.Count && overrideMaterials[i] != null ? overrideMaterials[i] : material;
                        }

                        mat.PopulateTextures();
                        mat.AddToObj(matsObj);
                    }
                }

                var children = new JArray();
                comp.Add(Program.PackageIndexToDirPath(mesh));
                comp.Add(matsObj);
                comp.Add(textureDataArr);
                comp.Add(Program.Vector(actor.GetOrDefault<FVector>("RelativeLocation"))); // /Script/Engine.SceneComponent:RelativeLocation
                comp.Add(Program.Rotator(actor.GetOrDefault<FRotator>("RelativeRotation"))); // /Script/Engine.SceneComponent:RelativeRotation
                comp.Add(Program.Vector(actor.GetOrDefault<FVector>("RelativeScale3D", FVector.OneVector))); // /Script/Engine.SceneComponent:RelativeScale3D
                comp.Add(children);
            }

            var pkg = obj.Owner;
            string pkgName = Program.provider.CompactFilePath(pkg.Name).SubstringAfter("/");
            var file = new FileInfo(Path.Combine(MyFileProvider.JSONS_FOLDER.ToString(), pkgName + ".processed.json"));
            file.Directory.Create();
            Log.Information("Writing to {0}", file.FullName);

            using var writer = file.CreateText();
            new JsonSerializer().Serialize(writer, comps);            
        }
    }
}