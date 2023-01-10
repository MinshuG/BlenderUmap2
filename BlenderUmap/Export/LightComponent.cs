using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Objects.Core.Math;
using Newtonsoft.Json;

namespace BlenderUmap;

public class ULightComponent: UObject {
    protected override void WriteJson(JsonWriter writer, JsonSerializer serializer) {
        base.WriteJson(writer, serializer);
#if DEBUG
        writer.WritePropertyName("RelativeRotationQuat");
        serializer.Serialize(writer, GetOrDefault<FRotator>("RelativeRotation", FRotator.ZeroRotator).GetNormalized().Quaternion());
#endif
        writer.WritePropertyName("RelativeRotation");
        serializer.Serialize(writer, GetOrDefault<FRotator>("RelativeRotation", this is not URectLightComponent ? new FRotator(-90,0,0): FRotator.ZeroRotator));
    }
}

public class USpotLightComponent: ULightComponent { }
public class UPointLightComponent: ULightComponent { }
public class URectLightComponent: ULightComponent { }
