from io import StringIO
import os
import zipfile
import glob

try:
    version = os.popen("git rev-list --count HEAD").read().strip()
    int(version)
    branch = os.popen("git rev-parse --abbrev-ref HEAD").read().strip()
except ValueError:
    version = "0"

minor = version[-1:]
major = version[:-1]
version = f"{major}.{minor}"

print(f"version: {version}")

version_f = StringIO()
version_f.write(f"__version__ = '{version}'\n")
version_f.write(f"branch = '{branch}'")

def add_files_to_zip(zip_file: zipfile.ZipFile, pattern, prefix=''):
    for file in glob.glob(pattern):
        zip_file.write(file, os.path.join(prefix, os.path.basename(file)))

try: os.mkdir('release')
except FileExistsError: pass

for target in ["osx.12-x64", "win-x64", "linux-x64"]:
    try:
        for f in glob.glob("./BlenderUmap/bin/Publish/**"):
            os.remove(f)
    except FileNotFoundError: pass

    code = os.system("dotnet publish BlenderUmap -c Release -r %s --no-self-contained -o \"./BlenderUmap/bin/Publish/\" -p:PublishSingleFile=true -p:DebugType=None -p:DebugSymbols=false -p:IncludeAllContentForSelfExtract=true -p:AssemblyVersion=%s -p:FileVersion=%s"%(target, version, version))
    if code != 0:
        raise Exception(f"dotnet publish failed with code {code}")
    zipf = zipfile.ZipFile(f'release/BlenderUmap-{target}.zip', 'w', zipfile.ZIP_DEFLATED, allowZip64=True, compresslevel=9)
    add_files_to_zip(zipf, "./BlenderUmap/bin/Publish/**", "BlenderUmap/")
    add_files_to_zip(zipf, "./Addon/*.py", "BlenderUmap/")

    zipf.writestr("BlenderUmap/__version__.py", version_f.getvalue())
    zipf.close()
version_f.close()
