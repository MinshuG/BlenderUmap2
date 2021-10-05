using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Assets;
using CUE4Parse.UE4.Objects.Core.Misc;
using CUE4Parse.UE4.Versions;
using CUE4Parse.Utils;
using Newtonsoft.Json;

namespace BlenderUmap {
    public class MyFileProvider : DefaultFileProvider {
        public static readonly DirectoryInfo JSONS_FOLDER = new("jsons");
        private readonly Cache _cache;
        private readonly bool _bDumpAssets; 

        public MyFileProvider(string folder, EGame game, List<EncryptionKey> encryptionKeys, bool bDumpAssets, int cacheSize) : base(folder, SearchOption.AllDirectories, true, new VersionContainer(game)) {
            _cache = new Cache(cacheSize);
            _bDumpAssets = bDumpAssets;

            var keysToSubmit = new Dictionary<FGuid, FAesKey>();
            foreach (var entry in encryptionKeys) {
                if (!string.IsNullOrEmpty(entry.FileName)) {
                    var foundGuid = UnloadedVfs.FirstOrDefault(it => it.Name == entry.FileName);

                    if (foundGuid != null) {
                        keysToSubmit[foundGuid.EncryptionKeyGuid] = new FAesKey(entry.Key);
                    } else {
                        Log.Warning("PAK file not found: {0}", entry.FileName);
                    }
                } else {
                    keysToSubmit[entry.Guid] = new FAesKey(entry.Key);
                }
            }

            Initialize();
            SubmitKeys(keysToSubmit);
        }

        public override bool TryLoadPackage(string path, out IPackage package) {
            if (_cache.TryGet(path, out package))
                return true;
            else {
                if (base.TryLoadPackage(path, out package)) {
                    if (_cache.Size != 0)
                        _cache.Add(path, package);
                    if (_bDumpAssets)
                        DumpJson(package);
                    return true;
                }
            }
            return false;
        }

        public void DumpJson(IPackage package) {
            var output = new FileInfo(Path.Combine(Program.GetExportDir(package).ToString(), package.Name.SubstringAfterLast("/") + ".json"));
            if (output.Exists) 
                return;
            using var writer = new StreamWriter(output.FullName);
            writer.Write(JsonConvert.SerializeObject(package.GetExports(), Formatting.Indented));
        }

        // WARNING: This does convert FortniteGame/Plugins/GameFeatures/GameFeatureName/Content/Package into /GameFeatureName/Package
        public string CompactFilePath(string path) {
            if (path[0] == '/') {
                return path;
            }

            if (path.StartsWith("Engine/Content")) { // -> /Engine
                return "/Engine" + path["Engine/Content".Length..];
            }

            if (path.StartsWith("Engine/Plugins")) { // -> /Plugins
                return path["Engine".Length..];
            }

            var delim = path.IndexOf("/Content/", StringComparison.Ordinal);
            if (delim == -1) {
                return path;
            }

            // GameName/Content -> /Game
            return "/Game" + path[(delim + "/Content".Length)..];
        }
    }

    public class Cache {
        public readonly int Size = 100;
        private readonly Dictionary<string, IPackage> _cache;

        public Cache(int size) {
            Size = size;
            _cache = new Dictionary<string, IPackage>(StringComparer.OrdinalIgnoreCase);
        }

        public bool TryGet(string path, out IPackage package) {
            return _cache.TryGetValue(path, out package);
        }

        public void Add(string path, IPackage package) {
            if (_cache.ContainsKey(path))
                return;
            if (_cache.Count == Size) {
                _cache.Remove(_cache.Keys.First());
            }
            _cache.Add(path, package);
        }
    }
    public class EncryptionKey {
        public FGuid Guid;
        public string FileName;
        public string Key;

        public EncryptionKey() {
            Guid = new();
            Key = String.Empty;
        }

        public EncryptionKey(FGuid guid, string key) {
            Guid = guid;
            Key = key;
        }
    }
}