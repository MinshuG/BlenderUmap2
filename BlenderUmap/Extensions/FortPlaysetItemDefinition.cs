using System;
using System.Collections.Generic;
using System.IO;
using CUE4Parse.GameTypes.FN.Assets.Exports;
using CUE4Parse.UE4.Assets;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Objects;
using CUE4Parse.UE4.Objects.Core.Math;
using CUE4Parse.UE4.Objects.Engine;
using CUE4Parse.UE4.Objects.UObject;
using CUE4Parse.Utils;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Serilog;

namespace BlenderUmap.Extensions {
    public static class FortPlaysetItemDefinition {
        public static IPackage ExportAndProduceProcessed(UObject obj, MyFileProvider provider) {
            var comps = new JArray();
            var recordLazy = obj.GetOrDefault<FPackageIndex>("PlaysetPropLevelSaveRecordCollection");
            if (recordLazy == null || recordLazy.IsNull) return null;

            var records = recordLazy.Load()!.GetOrDefault<FStructFallback[]>("Items");
            for (var index = 0; index < records.Length; index++) {
                if (index % 100 == 0) { // every 100th actor
                    GC.Collect();
                }
                
                var record = records[index];
                var actorRecord = record.GetOrDefault<UObject>("LevelSaveRecord").GetOrDefault<ULevelSaveRecord>("ActorSaveRecord");

                FActorTemplateRecord templeteRecords = null;
                foreach (var kv in actorRecord.GetOrDefault<UScriptMap>("TemplateRecords").Properties) {
                    var val = kv.Value.GetValue(typeof(FActorTemplateRecord));
                    templeteRecords = val is FActorTemplateRecord rec ? rec : null;
                    break; // TODO what about others? FortniteGame/Content/Playsets/PID_Playset_105x105_Composed_Loki_06
                }
                if (templeteRecords is null) continue;

                var ac = templeteRecords.ActorClass.Load();
                if (ac == null) continue;
                Log.Information("Loading {0}: {1}/{2} {3}", obj.Name, index, records.Length, ac);

                var comp = new JArray();
                comps.Add(comp);
                comp.Add(Guid.NewGuid().ToString().Replace("-", ""));
                comp.Add(record.GetOrDefault<FName>("RecordUniqueName").ToString());

                UObject staticMeshComp = new UObject();
                UObject actorBlueprint = new UObject();
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
                    var material = ac.GetOrDefault<FPackageIndex>("BaseMaterial");
                    var overrideMaterials = staticMeshComp?.GetOrDefault<List<FPackageIndex>>("OverrideMaterials");

                    var actorDatas = templeteRecords.ReadActorData(actorRecord.Owner, actorRecord.SaveVersion);

                    foreach (var tdPkg in actorDatas.GetProps<string>("TextureData")) { // /Script/FortniteGame.BuildingSMActor:TextureData
                        if (provider.TryLoadObject(tdPkg, out var td)) {
                            var textures = new JArray();
                            Program.AddToArray(textures, td.GetOrDefault<FPackageIndex>("Diffuse"));
                            Program.AddToArray(textures, td.GetOrDefault<FPackageIndex>("Normal"));
                            Program.AddToArray(textures, td.GetOrDefault<FPackageIndex>("Specular"));
                            textureDataArr.Add(new JArray { Program.PackageIndexToDirPath(td), textures });
                            var overrideMaterial = td.GetOrDefault<FPackageIndex>("OverrideMaterial");
                            if (overrideMaterial != null) {
                                material = overrideMaterial;
                            }
                        }
                        else {
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

                if (record.TryGetValue(out FStructFallback transform, "Transform")) {
                    comp.Add(Program.Vector(transform.GetOrDefault<FVector>("Translation")));
                    var rot = transform.GetOrDefault<FQuat>("Rotation");
                    //var rot = actorRecord.GetOrDefault<FRotator>("Rotation"); // what is this for?
                    comp.Add(Program.Rotator(rot.Rotator()));
                    comp.Add(Program.Vector(transform.GetOrDefault<FVector>("Scale3D", FVector.OneVector)));
                }
                else {
                    continue;
                    // comp.Add(Program.Vector(actorRecord.GetOrDefault<FVector>("RelativeLocation")));
                    // comp.Add(Program.Rotator(actorRecord.GetOrDefault<FRotator>("RelativeRotation")));
                    // comp.Add(Program.Vector(actorRecord.GetOrDefault<FVector>("RelativeScale3D", FVector.OneVector)));    
                }
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
            file.Directory?.Create();
            Log.Information("Writing to {0}", file.FullName);

            using var writer = file.CreateText();
            new JsonSerializer().Serialize(writer, comps);
            return pkg;
        }
    }
}