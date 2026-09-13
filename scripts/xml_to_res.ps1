# xml_to_res.ps1 - converts a .yft.xml / .ydd.xml / .ydr.xml / .ybn.xml / .ypt.xml /
# .ytd.xml file into a game-ready binary. It is the REVERSE of res_to_xml.ps1.
#
# WHY IT IS NEEDED: sometimes you have to dump an asset to XML, fix it by hand (e.g. remove
# a broken node) and compile it back. Sollumz cannot do this; CodeWalker.Core
# can, but it has to be called without the GUI.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File xml_to_res.ps1 -XmlPath <...>.yft.xml
#   powershell -NoProfile -ExecutionPolicy Bypass -File xml_to_res.ps1 -XmlPath <...>.ydd.xml -OutPath <...>.ydd

param(
    [Parameter(Mandatory=$true)][string] $XmlPath,
    [string] $OutPath,
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

# CAREFUL: if the path contains square brackets such as [peds], Test-Path reads them as a
# WILDCARD and cannot find the file -> -LiteralPath is required.
if (-not (Test-Path -LiteralPath $XmlPath)) { throw "XML not found: $XmlPath" }
if (-not $OutPath) { $OutPath = $XmlPath -replace '\.xml$', '' }

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
using System.Xml;
using CodeWalker.GameFiles;

public static class XmlToRes
{
    public static void Run(string xmlPath, string outPath)
    {
        var doc = new XmlDocument();
        doc.Load(xmlPath);

        string name = Path.GetFileName(outPath);
        string ext  = Path.GetExtension(outPath).ToLowerInvariant();
        byte[] data = null;

        switch (ext)
        {
            case ".yft":
            {
                var yft = XmlYft.GetYft(doc);
                if (yft == null) { Console.WriteLine("[!] XmlYft.GetYft returned null."); return; }
                data = yft.Save();
                break;
            }
            case ".ydd":
            {
                var ydd = XmlYdd.GetYdd(doc);
                if (ydd == null) { Console.WriteLine("[!] XmlYdd.GetYdd returned null."); return; }
                data = ydd.Save();
                break;
            }
            case ".ydr":
            {
                var ydr = XmlYdr.GetYdr(doc);
                if (ydr == null) { Console.WriteLine("[!] XmlYdr.GetYdr returned null."); return; }
                data = ydr.Save();
                break;
            }
            case ".ybn":
            {
                var ybn = XmlYbn.GetYbn(doc);
                if (ybn == null) { Console.WriteLine("[!] XmlYbn.GetYbn returned null."); return; }
                data = ybn.Save();
                break;
            }
            case ".ypt":
            {
                // Embedded textures (.dds) are looked up in the SAME folder as the XML; res_to_xml
                // already writes them there. If the folder is wrong the texture is not silently dropped;
                // XmlYpt returns null.
                var inputFolder = Path.GetDirectoryName(Path.GetFullPath(xmlPath));
                var ypt = XmlYpt.GetYpt(doc, inputFolder);
                if (ypt == null) { Console.WriteLine("[!] XmlYpt.GetYpt returned null."); return; }
                data = ypt.Save();
                break;
            }
            case ".ytd":
            {
                // Texture dictionary. Like .ypt, the .dds files named by <FileName>
                // are looked up in the SAME folder as the XML.
                //
                // WHY IT IS NEEDED: Sollumz can skip building a .ytd for a drawable
                // (measured: three drawables were exported, a .ytd was written for only
                // one of them; the component model's textures went into no
                // dictionary and would have shown up untextured in the game). There is no
                // fix other than compiling the .ytd by hand.
                var ytdFolder = Path.GetDirectoryName(Path.GetFullPath(xmlPath));
                var ytd = XmlYtd.GetYtd(doc, ytdFolder);
                if (ytd == null) { Console.WriteLine("[!] XmlYtd.GetYtd returned null."); return; }
                data = ytd.Save();
                break;
            }
            default:
                Console.WriteLine("[!] unsupported extension: " + ext);
                return;
        }

        File.WriteAllBytes(outPath, data);
        Console.WriteLine(string.Format("[+] {0,-42} -> {1:N0} bytes", name, data.Length));
    }
}
'@

$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'),
          'netstandard', 'System.Xml',
          # Under PowerShell 7 (.NET 8+) these types are forwarded from
          # netstandard; without a reference Add-Type crashes with CS1069/CS0103.
          # For XmlDocument 'System.Xml' is NOT ENOUGH -> 'System.Xml.ReaderWriter'
          # is needed. Do NOT ADD 'System.Private.Xml': it defines the same type too and
          # gives CS0433 (type exists in both assemblies).
          'System.Xml.ReaderWriter',
          'System.Collections', 'System.Runtime', 'System.Linq',
          'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[XmlToRes]::Run((Resolve-Path -LiteralPath $XmlPath).Path, $OutPath)
