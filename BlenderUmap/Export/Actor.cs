using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Readers;
using CUE4Parse.UE4.Versions;

namespace BlenderUmap;

public class AActor : UObject {
    public string ActorLabel = "None";
    public override void Deserialize(FAssetArchive Ar, long validPos) {
        base.Deserialize(Ar, validPos);
        if (FUE5PrivateFrostyStreamObjectVersion.Get(Ar) >= FUE5PrivateFrostyStreamObjectVersion.Type.SerializeActorLabelInCookedBuilds)
        {
            if (Ar.ReadBoolean()) {
                ActorLabel = Ar.ReadFString();
            }
        }
    }
}

public class AWorldSettings: AActor { }
public class AStaticMeshActor: AActor { }
public class ALight: AActor { }
public class ASpotLight : ALight { }
public class APointLight : ALight { }
public class ARectLight : ALight { }
