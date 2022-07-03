import os
import zipfile
import glob


def add_files_to_zip(zip_file: zipfile.ZipFile, pattern, prefix=''):
    for file in glob.glob(pattern):
        zip_file.write(file, os.path.join(prefix, os.path.basename(file)))

try: os.mkdir('release')
except FileExistsError: pass

for target in ["win-x64", "osx-x64", "linux-x64"]:
    try:
        for f in glob.glob("./BlenderUmap/bin/Publish/**"):
            os.remove(f)
    except FileNotFoundError: pass

    code = os.system(f"dotnet publish BlenderUmap -c Release -r {target} --no-self-contained -o \"./BlenderUmap/bin/Publish/\" -p:PublishSingleFile=true -p:DebugType=None -p:DebugSymbols=false -p:IncludeAllContentForSelfExtract=true")
    if code != 0:
        raise Exception(f"dotnet publish failed with code {code}")
    zipf = zipfile.ZipFile(f'release/BlenderUmap-{target}.zip', 'w', zipfile.ZIP_LZMA, allowZip64=True, compresslevel=9)
    add_files_to_zip(zipf, "./BlenderUmap/bin/Publish/**", "BlenderUmap/")
    add_files_to_zip(zipf, "./Addon/*.py", "BlenderUmap/")
    zipf.close()
