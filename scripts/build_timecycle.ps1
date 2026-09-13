# build_timecycle.ps1 - GTA V TIMECYCLE MODIFIER CATALOG.
#
# WHY: when a prop looks dark inside an interior, the cause is usually not the prop but
# the room's TIMECYCLE MODIFIER. A room is bound to a modifier by `timecycleName`;
# that modifier overrides ambient light, fog density and exposure. If you set the light up
# correctly and still see "dark", this is the reason -- and it cannot be guessed
# without looking at this file.
#
# IMPORTANT: the same file name (timecycle_mods_1.xml) exists in SEVERAL DLC rpfs.
# Extracting by name with extract_asset.ps1 SILENTLY overwrites them
# (4 of 12 files remain). So here we walk the RPFs ourselves and every
# row is written together with WHICH RPF it came from. If several DLCs define the
# same modifier, all of them are recorded; which one wins depends on the DLC load
# order and CANNOT BE READ from this file -- so it is shown, not hidden.
#
# XML STRUCTURE:
#   <timecycle_modifier_data>
#     <modifier name="li" numMods="32" userFlags="0">
#       <light_dir_col_r>0.886 0.000</light_dir_col_r>   <- value1 value2
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_timecycle.ps1

param(
    [string] $GtaFolder,
    [string] $CodeWalker,
    [string] $Out
)

$ErrorActionPreference = 'Stop'

if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent) 'data' }
if (-not (Test-Path -LiteralPath $Out)) { New-Item -ItemType Directory -Path $Out | Out-Null }

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path -LiteralPath $CodeWalker)) { throw "CodeWalker.Core.dll not found." }
$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V folder not found." }

$cwDir = Split-Path $CodeWalker -Parent
Write-Output "CodeWalker : $CodeWalker"
Write-Output "GTA V      : $GtaFolder"

$script:cwDir = $cwDir
[System.AppDomain]::CurrentDomain.add_AssemblyResolve([System.ResolveEventHandler]{
    param($sender, $e)
    $short = ($e.Name -split ',')[0]
    $p = Join-Path $script:cwDir "$short.dll"
    if (Test-Path -LiteralPath $p) { return [System.Reflection.Assembly]::LoadFrom($p) }
    return $null
})

$src = @'
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Text;
using System.Xml;
using CodeWalker.GameFiles;

public static class TimecycleIndexer
{
    static string Clean(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        return s.Replace('\t', ' ').Replace('\n', ' ').Replace('\r', ' ').Trim();
    }

    public static void Run(string gtaFolder, string outFolder)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        var files = new List<RpfFileEntry>();
        foreach (var rpf in man.AllRpfs)
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null) continue;
                var n = fe.NameLower;
                if (n.StartsWith("timecycle_mods") && n.EndsWith(".xml")) files.Add(fe);
            }
        Console.WriteLine("[*] timecycle_mods files: {0}", files.Count);

        var t0 = DateTime.Now;
        var sb = new StringBuilder(1 << 22);
        sb.Append("modifier\tparam\tvalue1\tvalue2\tnumMods\tsource\n");

        var modSources = new Dictionary<string, int>();      // name -> how many sources define it
        int nRows = 0, errors = 0;
        string firstError = null;

        foreach (var fe in files)
        {
            try
            {
                var data = fe.File.ExtractFile(fe);
                if (data == null || data.Length == 0) { errors++; continue; }
                var text = Encoding.UTF8.GetString(data);
                var doc = new XmlDocument();
                doc.LoadXml(text);

                // Source = path of the containing rpf; the same file name exists in several DLCs.
                string source = fe.File.Path + "/" + fe.Name;

                var mods = doc.SelectNodes("//modifier");
                foreach (XmlNode m in mods)
                {
                    var nameAttr = m.Attributes["name"];
                    if (nameAttr == null) continue;
                    string name = Clean(nameAttr.Value);
                    if (name.Length == 0) continue;
                    string numMods = "";
                    var nmAttr = m.Attributes["numMods"];
                    if (nmAttr != null) numMods = nmAttr.Value;

                    if (modSources.ContainsKey(name)) modSources[name] = modSources[name] + 1; else modSources[name] = 1;

                    foreach (XmlNode p in m.ChildNodes)
                    {
                        if (p.NodeType != XmlNodeType.Element) continue;
                        var parts = Clean(p.InnerText).Split(new char[] { ' ', '\t' },
                                                             StringSplitOptions.RemoveEmptyEntries);
                        string v1 = (parts.Length > 0) ? parts[0] : "";
                        string v2 = (parts.Length > 1) ? parts[1] : "";
                        sb.Append(name).Append('\t')
                          .Append(Clean(p.Name)).Append('\t')
                          .Append(v1).Append('\t').Append(v2).Append('\t')
                          .Append(numMods).Append('\t')
                          .Append(Clean(source)).Append('\n');
                        nRows++;
                    }
                }
            }
            catch (Exception ex)
            {
                errors++;
                if (firstError == null) firstError = fe.Name + ": " + ex.Message;
            }
        }

        Console.WriteLine("[*] files read: {0}, errors: {1}", files.Count - errors, errors);
        if (firstError != null) Console.WriteLine("[!] first error: {0}", firstError);

        int multiSource = 0;
        foreach (var kv in modSources) if (kv.Value > 1) multiSource++;

        var outPath = Path.Combine(outFolder, "timecycle.tsv.gz");
        var raw = Encoding.UTF8.GetBytes(sb.ToString());
        using (var fs = File.Create(outPath))
        using (var gz = new GZipStream(fs, CompressionLevel.Optimal))
            gz.Write(raw, 0, raw.Length);

        Console.WriteLine("[+] timecycle.tsv.gz  ({0} unique modifiers / {1} parameter rows)",
                          modSources.Count, nRows);
        Console.WriteLine("[+] modifiers defined in more than one source: {0}", multiSource);
        Console.WriteLine("[+] {0:0.0} s", (DateTime.Now - t0).TotalSeconds);
    }
}
'@

$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'mscorlib', 'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console',
          'System.IO.Compression', 'System.Xml', 'System.Xml.ReaderWriter')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[TimecycleIndexer]::Run($GtaFolder, $Out)
