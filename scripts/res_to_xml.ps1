# res_to_xml.ps1 - dumps a binary .ycd / .yed / .yft / .ydd / .yld / .ypt file to XML.
#
# WHY IT IS NEEDED: Sollumz CANNOT READ binary .ycd and .yed. When you try to import one it
# silently shows the warning
#     "Binary resource format '.ycd' is not supported yet."
# and says "Imported in 0.0 seconds" - it throws no error, and nothing arrives
# in the scene either. To inspect an animation frame by frame in Blender you MUST
# convert it to XML first.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File res_to_xml.ps1 -Path <file>
#   powershell -NoProfile -ExecutionPolicy Bypass -Command "& res_to_xml.ps1 -Path @('a.ycd','b.yed')"
#   powershell -NoProfile -ExecutionPolicy Bypass -File res_to_xml.ps1 -Dir <folder> -Filter *.ycd
#
# Output: <same name>.xml  (or in -OutDir if given)

param(
    [string[]] $Path = @(),
    [string]   $Dir,
    [string]   $Filter = '*.ycd',
    [string]   $OutDir,
    [string]   $CodeWalker
)

$ErrorActionPreference = 'Stop'

if ($Dir) {
    if (-not (Test-Path -LiteralPath $Dir)) { throw "Folder not found: $Dir" }
    $Path += (Get-ChildItem -LiteralPath $Dir -Filter $Filter -File | ForEach-Object { $_.FullName })
}
if ($Path.Count -eq 0) { throw "No file given. Use -Path or -Dir." }

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) { throw "CodeWalker.Core.dll not found." }

$cwDir = Split-Path $CodeWalker -Parent
$script:cwDir = $cwDir
[System.AppDomain]::CurrentDomain.add_AssemblyResolve([System.ResolveEventHandler]{
    param($sender, $e)
    $short = ($e.Name -split ',')[0]
    $p = Join-Path $script:cwDir "$short.dll"
    if (Test-Path $p) { return [System.Reflection.Assembly]::LoadFrom($p) }
    return $null
})

$src = @'
using System;
using System.IO;
using CodeWalker.GameFiles;

public static class ResToXml
{
    public static string One(string path, string outDir)
    {
        var data = File.ReadAllBytes(path);
        var name = Path.GetFileName(path);
        var ext  = Path.GetExtension(path).ToLowerInvariant();
        string xml = null;

        switch (ext)
        {
            case ".ycd":
            {
                var f = RpfFile.GetResourceFile<YcdFile>(data);
                f.Name = name;
                xml = YcdXml.GetXml(f);
                break;
            }
            case ".yed":
            {
                var f = RpfFile.GetResourceFile<YedFile>(data);
                f.Name = name;
                xml = YedXml.GetXml(f);
                break;
            }
            case ".yft":
            {
                var f = RpfFile.GetResourceFile<YftFile>(data);
                f.Name = name;
                xml = YftXml.GetXml(f);
                break;
            }
            case ".ydd":
            {
                var f = RpfFile.GetResourceFile<YddFile>(data);
                f.Name = name;
                xml = YddXml.GetXml(f);
                break;
            }
            case ".ydr":
            {
                var f = RpfFile.GetResourceFile<YdrFile>(data);
                f.Name = name;
                xml = YdrXml.GetXml(f);
                break;
            }
            case ".yld":
            {
                // Ped cloth dictionary (the same-named file next to the .ydd)
                var f = RpfFile.GetResourceFile<YldFile>(data);
                f.Name = name;
                xml = YldXml.GetXml(f);
                break;
            }
            case ".ybn":
            {
                var f = RpfFile.GetResourceFile<YbnFile>(data);
                f.Name = name;
                xml = YbnXml.GetXml(f);
                break;
            }
            case ".ymt":
            {
                // Ped variation / creature metadata etc. A Meta/PSO resource; its own Load, like ytyp.
                var f = new YmtFile();
                f.Load(data);
                f.Name = name;
                string _fn;
                xml = MetaXml.GetXml(f, out _fn);
                break;
            }
            case ".ytyp":
            {
                // CAREFUL: .ytyp is a Meta/PSO resource; it CANNOT be read with RpfFile.GetResourceFile<YtypFile>
                // -> it crashes with StackOverflowException. Its own Load is used
                // and the XML is produced by MetaXml (there is NO class called YtypXml).
                var f = new YtypFile();
                f.Load(data);
                string _fn;
                xml = MetaXml.GetXml(f, out _fn);
                break;
            }
            case ".ytd":
            {
                // Texture dictionary. Like .ypt: the embedded .dds files are written to the output folder
                // as SEPARATE files; they must be in the same folder when compiling back.
                var f = RpfFile.GetResourceFile<YtdFile>(data);
                f.Name = name;
                var tdir = string.IsNullOrWhiteSpace(outDir) ? Path.GetDirectoryName(path) : outDir;
                if (!Directory.Exists(tdir)) Directory.CreateDirectory(tdir);
                xml = YtdXml.GetXml(f, tdir);
                break;
            }
            case ".ypt":
            {
                // Particle effect. The difference from the others: the embedded .dds textures
                // are written to the output folder as SEPARATE files; when compiling back
                // (xml_to_res.ps1) those files must be in the same folder as the XML.
                var f = RpfFile.GetResourceFile<YptFile>(data);
                f.Name = name;
                var texDir = string.IsNullOrWhiteSpace(outDir) ? Path.GetDirectoryName(path) : outDir;
                if (!Directory.Exists(texDir)) Directory.CreateDirectory(texDir);
                xml = YptXml.GetXml(f, texDir);
                break;
            }
            default:
                Console.WriteLine("[!] {0}: unsupported extension", name);
                return null;
        }

        if (string.IsNullOrEmpty(xml)) { Console.WriteLine("[!] {0}: XML empty", name); return null; }

        var dir = string.IsNullOrWhiteSpace(outDir) ? Path.GetDirectoryName(path) : outDir;
        if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
        var dst = Path.Combine(dir, name + ".xml");
        File.WriteAllText(dst, xml);
        Console.WriteLine("[+] {0,-52} -> {1:N0} bytes XML", name, xml.Length);
        return dst;
    }

    public static void Run(string[] paths, string outDir)
    {
        int ok = 0, bad = 0;
        foreach (var p in paths)
        {
            try { if (One(p, outDir) != null) ok++; else bad++; }
            catch (Exception ex) { Console.WriteLine("[!] {0}: {1}", Path.GetFileName(p), ex.Message); bad++; }
        }
        Console.WriteLine("[=] {0} succeeded, {1} failed", ok, bad);
    }
}
'@

# 'System.Collections'/'System.Runtime'/'System.Console' are REQUIRED: under PowerShell 7 (.NET 8+)
# these types are FORWARDED from netstandard; without a reference
# Add-Type crashes with "CS1069: type has been forwarded" / "CS0103: Console does not exist".
# Windows PowerShell 5.1 has no problem with it; PS7 fails every time.
$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard', 'System.Xml',
          'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[ResToXml]::Run($Path, $OutDir)
