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
            var actors = obj.GetOrDefault<FStructFallback[]>("PreviewActorData");
            for (var index = 0; index < actors.Length; index++) {
                var actor = actors[index];
                var comp = new JArray();
                var ac = actor.GetOrDefault<UObject>("ActorClass");
                if (ac == null) continue;
                Log.Information("Loading {0}: {1}/{2} {3}", obj.Name, index, actors.Length, ac);

                comps.Add(comp);
                comp.Add(Guid.NewGuid().ToString().Replace("-", ""));
                comp.Add(ac.Name.SubstringBefore("_C"));

                var staticMeshComp = new UObject();
                var actorBlueprint = new UObject();
                var mesh = new FPackageIndex();
                if (ac is UBlueprintGeneratedClass ab) {
                    actorBlueprint = ab.ClassDefaultObject.Load();
                    mesh = actorBlueprint?.GetOrDefault<FPackageIndex>("StaticMesh");
                    staticMeshComp = actorBlueprint?.GetOrDefault<UObject>("StaticMeshComponent");
                }

                var matsObj = new JObject(); // matpath: [4x[str]]
                var textureDataArr = new JArray();
                var materials = new List<Program.Mat>();
                Program.ExportMesh(mesh, materials);
                
                if (Program.config.bReadMaterials) {
                    var material = actor.GetOrDefault<FPackageIndex>("BaseMaterial"); // /Script/FortniteGame.BuildingSMActor:BaseMaterial
                    var overrideMaterials = staticMeshComp?.GetOrDefault<List<FPackageIndex>>("OverrideMaterials"); // /Script/Engine.MeshComponent:OverrideMaterials

                    foreach (var textureDataIdx in actorBlueprint.GetProps<FPackageIndex>("TextureData")) { // /Script/FortniteGame.BuildingSMActor:TextureData
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
                            var matIndex = overrideMaterials != null && i < overrideMaterials.Count && overrideMaterials[i] != null ? overrideMaterials[i] : material;
                            mat.Material = matIndex?.ResolvedObject;
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

            // if (obj.TryGetValue(out FSoftObjectPath child, "PlaysetToSpawn")) {
            //     var children = new JArray();
            //     var childPackage = Program.ExportAndProduceProcessed(child.AssetPathName.Text);
            //
            //     children.Add(childPackage != null ? Program.provider.CompactFilePath(childPackage.Name) : null);  
            //     var comp = new JArray {
            //         JValue.CreateNull(), // GUID
            //         childPackage.Name,
            //         JValue.CreateNull(), // mesh path
            //         JValue.CreateNull(), // materials
            //         JValue.CreateNull(), // texture data
            //         Program.Vector(new FVector()), // location
            //         Program.Quat(new FQuat()), // rotation
            //         Program.Vector(new FVector(1)), // scale
            //         children
            //     };
            //     comps.Add(comp);
            // }

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