# BlenderUmap
BlenderUmap is tool export .umap from UE4/5 Games.

BlenderUmap can also read .replay files from Fortnite and export actors from them.

## Requirements
- Blender 3.0 or higher
- [dotnet 6 runtime](https://dotnet.microsoft.com/en-us/download/dotnet/6.0)

## Build Requirements
- [dotnet 6 sdk](https://dotnet.microsoft.com/en-us/download/dotnet/6.0)
- windows sdk (windows only)
- CPP compiler

## Installation
0. Clone the repository using `git clone https://github.com/MinshuG/BlenderUmap2.git --recursive`
1. Installable addon can be generated using make_release.py (generated in ./release folder)
2. Open the Blender addon preferences menu (Edit > Preferences > Add-ons).
3. Click the Install and select the BlenderUmap-{platform}-x64.zip addon installation file.
4. Make sure you have psk/psa importer addon installed.
4. Enable the addon by activating the checkbox.
5. Restart Blender (if updating).

## Addon
<img src="./addon.png" alt="Addon Screenshot" height="500"/>
