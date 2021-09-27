using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Objects.Core.Misc;
using CUE4Parse.UE4.Objects.UObject;
using CUE4Parse.UE4.Versions;

namespace BlenderUmap {
    public class MyFileProvider : DefaultFileProvider {
        public static readonly DirectoryInfo JSONS_FOLDER = new("jsons");
        private Dictionary<string, UStruct> _structCache;
        private Dictionary<string, UEnum> _enumCache;

        public MyFileProvider(string folder, EGame game, List<EncryptionKey> encryptionKeys, bool bDumpAssets, int cacheSize) : base(folder, SearchOption.AllDirectories) {
            var keysToSubmit = new Dictionary<FGuid, FAesKey>();
            foreach (var entry in encryptionKeys) {
                if (!string.IsNullOrEmpty(entry.FileName)) {
                    var foundGuid = UnloadedVfs.FirstOrDefault(it => it.Name == entry.FileName);

                    if (foundGuid != null) {
                        keysToSubmit[foundGuid.EncryptionKeyGuid] = entry.Key;
                    } else {
                        Log.Warning("PAK file not found: {0}", entry.FileName);
                    }
                } else {
                    keysToSubmit[entry.Guid] = entry.Key;
                }
            }

            Initialize();
            SubmitKeys(keysToSubmit);
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

    public class EncryptionKey {
        public FGuid Guid;
        public string FileName;
        public FAesKey Key;

        public EncryptionKey() {
            Guid = new();
            Key = new FAesKey(new byte[32]);
        }

        public EncryptionKey(FGuid guid, FAesKey key) {
            Guid = guid;
            Key = key;
        }
    }
}