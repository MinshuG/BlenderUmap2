using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using CUE4Parse.FileProvider;
using CUE4Parse.MappingsProvider;
using CUE4Parse.UE4.Assets;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Exceptions;
using CUE4Parse.UE4.Objects.Core.Math;
using CUE4Parse.UE4.Objects.Engine;
using CUE4Parse.UE4.Objects.UObject;
using CUE4Parse.Utils;
using FortniteReplayReader;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Serilog;
using Unreal.Core.Models.Enums;

namespace BlenderUmap.Extensions;

public class NullPackage : AbstractUePackage {
    public NullPackage(string name, IFileProvider provider, TypeMappings mappings) : base(name, provider, mappings) {
    }

    public override FPackageFileSummary Summary => throw new NotImplementedException();

    public override FNameEntrySerialized[] NameMap => throw new NotImplementedException();

    public override Lazy<UObject>[] ExportsLazy => throw new NotImplementedException();

    public override bool IsFullyLoaded => throw new NotImplementedException();

    public override UObject GetExportOrNull(string name, StringComparison comparisonType = StringComparison.Ordinal) {
        throw new NotImplementedException();
    }

    public override ResolvedObject ResolvePackageIndex(FPackageIndex index) {
        throw new NotImplementedException();
    }
}

public static class ReplayExporter
{
    public static IPackage ExportAndProduceProcessed(string obj, MyFileProvider provider) {
            var comps = new JArray();
            var rr = new ReplayReader(null, ParseMode.Full);

            try {
                var replay = rr.ReadReplay(File.OpenRead(obj));
            }
            catch (Exception e) {
                //Console.WriteLine(e);
                throw new ParserException("corrupted or unsupported replay file");
            }

            var lights = new List<LightInfo2>();

            // var channels = rr.Channels.ToList().FindAll(x => x != null).ToArray();
            var actors = rr.Builder._actor_actors.Values.ToArray();
            for (var index = 0; index < actors.Length; index++)
            {
                // var channel = channels[index];
                // if (channel == null) continue;
                // if (channel.Actor == null || (channel.Actor.GetObject() == null || !provider.TryLoadObject(channel.Actor.GetObject(), out var record) ))
                //     continue;
                //
                var actor = actors[index];
                UObject record = null;
                // if (provider.TryLoadPackage(actor.GetObject(), out var pkg_)) {
                //     record = pkg_.GetExportOrNull("")
                // }

                if ((actor.GetObject() == null || !provider.TryLoadObject(actor.GetObject(), out record)))
                    continue;

                var ac = record;
                UObject staticMeshComp = new UObject();
                UObject actorBlueprint;
                FPackageIndex mesh = new FPackageIndex();
                if (ac is UBlueprintGeneratedClass ab) {
                    actorBlueprint = ab.ClassDefaultObject.Load();
                    mesh = actorBlueprint?.GetOrDefault<FPackageIndex>("StaticMesh");
                    staticMeshComp = actorBlueprint?.GetOrDefault<UObject>("StaticMeshComponent");

                    if (mesh == null && staticMeshComp == null) {
                        foreach (var export in actorBlueprint.Owner.GetExports()) {
                            if (export.ExportType == "StaticMeshComponent") {
                                staticMeshComp = export;
                                mesh = export.GetOrDefault("StaticMesh", new FPackageIndex());
                                break;
                            }
                        }
                    }
                }
                if (mesh == null || mesh.IsNull) continue;

                Log.Information("Loading {0}: {1}/{2} {3}", actor.Level, index, actors.Length, ac);

                var comp = new JArray();
                comps.Add(comp);
                comp.Add(Guid.NewGuid().ToString().Replace("-", ""));
                comp.Add(ac.Name);

                var matsObj = new JObject(); // matpath: [4x[str]]
                var textureDataArr = new JArray();
                var materials = new List<Program.Mat>();
                Program.ExportMesh(mesh, materials);

                if (Program.config.bReadMaterials) {
                    var material = ac.GetOrDefault<FPackageIndex>("BaseMaterial");
                    var overrideMaterials = staticMeshComp?.GetOrDefault<List<FPackageIndex>>("OverrideMaterials");

                    foreach (var textureDataIdx in ac.GetProps<FPackageIndex>("TextureData")) { // /Script/FortniteGame.BuildingSMActor:TextureData
                        var td = textureDataIdx?.Load();

                        if (td != null) {
                            var textures = new JArray();
                            Program.AddToArray(textures, td.GetOrDefault<FPackageIndex>("Diffuse"));
                            Program.AddToArray(textures, td.GetOrDefault<FPackageIndex>("Normal"));
                            Program.AddToArray(textures, td.GetOrDefault<FPackageIndex>("Specular"));
                            textureDataArr.Add(new JArray { Program.PackageIndexToDirPath(textureDataIdx), textures });
                            var overrideMaterial = td.GetOrDefault<FPackageIndex>("OverrideMaterial");
                            if (overrideMaterial is {IsNull: false}) {
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
                comp.Add(Vector(actor.Location));
                comp.Add(Rotator(actor.Rotation));
                comp.Add(Vector(actor.Scale));
                comp.Add(children);

                int LightIndex = -1;
                if (Program.CheckIfHasLights(ac.Owner, out var lightinfo)) {
                    var infor = new LightInfo2() {
#if DEBUG
                        Location = ToFVector(actor.Location), Rotation = ToRotator(actor.Rotation),
#endif
                        Props = lightinfo
                    };
#if DEBUG
                    infor.Location = infor.Location;
                    infor.Rotation = (infor.Rotation + lightinfo.GetOrDefault<FRotator>("RelativeRotation")).GetNormalized();
#endif
                    // X               Y                 Z
                    // rotator.Roll2, -rotator.Pitch0, -rotator.Yaw1
                    lights.Add(infor);
                    LightIndex = lights.Count - 1;
                }
                comp.Add(LightIndex);
            }

            string pkgName = "Replay\\" + obj.SubstringAfterLast("\\");
            var file = new FileInfo(Path.Combine(MyFileProvider.JSONS_FOLDER.ToString(), pkgName + ".processed.json"));
            file.Directory?.Create();
            Log.Information("Writing to {0}", file.FullName);

            using var writer = file.CreateText();
            new JsonSerializer().Serialize(writer, comps);

            var file2 = new FileInfo(Path.Combine(MyFileProvider.JSONS_FOLDER.ToString(), pkgName + ".lights.processed.json"));
            file2.Directory?.Create();

            using var writer2 = file2.CreateText();
#if DEBUG
            new JsonSerializer() { Formatting = Formatting.Indented }.Serialize(writer2, lights);
#else
            new JsonSerializer().Serialize(writer2, lights);
#endif

            return new NullPackage("/"+pkgName.Replace("\\", "/"), null, null);
    }

    public static JArray Vector(Unreal.Core.Models.FVector vector) => new() {vector.X, vector.Y, vector.Z};
    public static JArray Rotator(Unreal.Core.Models.FRotator rotator) => new() {rotator.Pitch, rotator.Yaw, rotator.Roll};
    public static JArray Quat(Unreal.Core.Models.FQuat quat) => new() {quat.X, quat.Y, quat.Z, quat.W};

    public static FVector ToFVector(Unreal.Core.Models.FVector vector) {
        return new FVector(vector.X, vector.Y, vector.Z);
    }

    public static FRotator ToRotator(Unreal.Core.Models.FRotator vector) {
        return new FRotator(vector.Pitch, vector.Yaw, vector.Roll);
    }
}