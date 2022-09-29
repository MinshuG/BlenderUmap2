using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Objects.Core.Math;
using Newtonsoft.Json;

namespace BlenderUmap;

public class LightComponent: UObject {
    protected override void WriteJson(JsonWriter writer, JsonSerializer serializer) {
        base.WriteJson(writer, serializer);
#if DEBUG
        writer.WritePropertyName("RelativeRotationQuat");
        serializer.Serialize(writer, GetOrDefault<FRotator>("RelativeRotation", FRotator.ZeroRotator).GetNormalized().Quaternion());
#endif
        writer.WritePropertyName("RelativeRotation");
        serializer.Serialize(writer, GetOrDefault<FRotator>("RelativeRotation", FRotator.ZeroRotator).GetNormalized());
    }
}

public class SpotLightComponent: LightComponent { }

public class PointLightComponent: LightComponent { }
