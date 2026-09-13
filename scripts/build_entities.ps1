# build_entities.ps1 - builds a WORLD position index from ymap placements.
#
# Two sources:
#   1) ymap root entities                -> world position directly
#   2) MLO instance + MLO archetype      -> world position of interior props
#      world = mloPos + rotate(localPos, mloRot)   [raw quaternion; verified]
#
# Verification: v_ilev_gb_teldr @ Legion Square = (145.4186, -1041.8130, 29.6426)
# This matches the independent measurement on the server (145.4186, -1041.8125, 29.6426).
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_entities.ps1 `
#       [-GtaFolder <path>] [-CodeWalker <dll>] [-Out <data>] [-All]
#
# Without -All, LOD/SLOD and terrain pieces are skipped (index ~10x smaller,
#  the props needed when writing scripts are kept).
#
# Output: data/entities.tsv.gz

param(
    [string] $GtaFolder,
    [string] $CodeWalker,
    [string] $Out,
    [switch] $All
)

$ErrorActionPreference = 'Stop'

if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent) 'data' }
if (-not (Test-Path $Out)) { New-Item -ItemType Directory -Path $Out -Force | Out-Null }

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker) {
    # Last resort: search the disk. SLOW (scans under C:\). To make it permanent:
    #   python assetdb.py path codewalker "<path>"
    $CodeWalker = Get-ChildItem -Path "$env:USERPROFILE\Desktop","C:\" -Filter 'CodeWalker.Core.dll' `
                    -Recurse -Depth 4 -ErrorAction SilentlyContinue |
                  Select-Object -First 1 -ExpandProperty FullName
}
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) { throw "CodeWalker.Core.dll not found. Pass it with -CodeWalker <path>." }

$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V folder not found. Pass it with -GtaFolder <path>." }

$cwDir = Split-Path $CodeWalker -Parent
Write-Output "CodeWalker : $CodeWalker"
Write-Output "GTA V      : $GtaFolder"
Write-Output "Mode       : $(if($All){'ALL entities'}else{'filtered (LOD/terrain excluded)'})"
Write-Output "Output     : $Out"

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
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using CodeWalker.GameFiles;
using SharpDX;

public static class EntityIndexer
{
    class Local { public string Name; public Vector3 Pos; }

    // LOD / terrain / cover pieces: never queried when writing
    // scripts, but they take up 90% of the index.
    static bool Skip(string n)
    {
        if (string.IsNullOrEmpty(n)) return true;
        if (n.IndexOf("slod", StringComparison.OrdinalIgnoreCase) >= 0) return true;
        if (n.EndsWith("_lod", StringComparison.OrdinalIgnoreCase)) return true;
        if (n.IndexOf("_lod_", StringComparison.OrdinalIgnoreCase) >= 0) return true;
        return false;
    }

    static string F(float v) { return v.ToString("0.###", CultureInfo.InvariantCulture); }

    public static void Run(string gtaFolder, string outFolder, bool all)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        var t0 = DateTime.Now;
        man.Init(gtaFolder, s => { }, s => { }, false, true);
        Console.WriteLine("[*] RPF scan: {0:0.0} s", (DateTime.Now - t0).TotalSeconds);

        var ytyps = new List<RpfFileEntry>();
        var ymaps = new List<RpfFileEntry>();
        foreach (var rpf in man.AllRpfs)
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null) continue;
                if (fe.NameLower.EndsWith(".ytyp")) ytyps.Add(fe);
                else if (fe.NameLower.EndsWith(".ymap")) ymaps.Add(fe);
            }
        Console.WriteLine("[*] ytyp={0}  ymap={1}", ytyps.Count, ymaps.Count);

        // -- 1) MLO archetype -> LOCAL positions of interior entities ---
        var mloLocals = new Dictionary<uint, List<Local>>();
        var mloNames = new Dictionary<uint, string>();
        int mloArch = 0, mloEnt = 0;
        foreach (var fe in ytyps)
        {
            try
            {
                var data = fe.File.ExtractFile(fe);
                if (data == null || data.Length == 0) continue;
                var y = new YtypFile(); y.Load(data, fe);
                if (y.AllArchetypes == null) continue;
                foreach (var a in y.AllArchetypes)
                {
                    var m = a as MloArchetype;
                    if (m == null || m.entities == null) continue;
                    mloArch++;
                    uint mh = m._BaseArchetypeDef.name.Hash;
                    mloNames[mh] = m.Name;
                    List<Local> list;
                    if (!mloLocals.TryGetValue(mh, out list)) { list = new List<Local>(); mloLocals[mh] = list; }
                    foreach (var me in m.entities)
                    {
                        var d = me.Data;
                        string nm = d.archetypeName.ToString();
                        if (!all && Skip(nm)) continue;
                        list.Add(new Local { Name = nm, Pos = d.position });
                        mloEnt++;
                    }
                }
            }
            catch { }
        }
        Console.WriteLine("[*] MLO archetypes={0}  interior entities={1}", mloArch, mloEnt);

        // -- 2) ymap -> root entities + MLO instance expansion ----------
        var outPath = Path.Combine(outFolder, "entities.tsv.gz");
        long root = 0, mlo = 0, skipped = 0;
        int okY = 0, errY = 0;
        var t1 = DateTime.Now;

        using (var fs = File.Create(outPath))
        using (var gz = new GZipStream(fs, CompressionLevel.Optimal))
        using (var w = new StreamWriter(gz))
        {
            w.Write("name\tx\ty\tz\tkind\tymap\tinterior\n");

            foreach (var fe in ymaps)
            {
                try
                {
                    var data = fe.File.ExtractFile(fe);
                    if (data == null || data.Length == 0) { errY++; continue; }
                    var y = new YmapFile(); y.Load(data, fe);
                    okY++;

                    var ceds = y.CEntityDefs;
                    if (ceds != null)
                        foreach (var ced in ceds)
                        {
                            string nm = ced.archetypeName.ToString();
                            if (!all && Skip(nm)) { skipped++; continue; }
                            var p = ced.position;
                            w.Write(nm); w.Write('\t');
                            w.Write(F(p.X)); w.Write('\t'); w.Write(F(p.Y)); w.Write('\t'); w.Write(F(p.Z));
                            w.Write("\troot\t"); w.Write(fe.Name); w.Write("\t\n");
                            root++;
                        }

                    var mis = y.CMloInstanceDefs;
                    if (mis != null)
                        foreach (var mi in mis)
                        {
                            var ced = mi.CEntityDef;
                            List<Local> locals;
                            if (!mloLocals.TryGetValue(ced.archetypeName.Hash, out locals)) continue;
                            var mloPos = ced.position;
                            // The raw quaternion is the right convention (verified with a known coordinate)
                            var q = new Quaternion(ced.rotation.X, ced.rotation.Y, ced.rotation.Z, ced.rotation.W);
                            string interior;
                            if (!mloNames.TryGetValue(ced.archetypeName.Hash, out interior)) interior = ced.archetypeName.ToString();
                            foreach (var lo in locals)
                            {
                                var wp = mloPos + Vector3.Transform(lo.Pos, q);
                                w.Write(lo.Name); w.Write('\t');
                                w.Write(F(wp.X)); w.Write('\t'); w.Write(F(wp.Y)); w.Write('\t'); w.Write(F(wp.Z));
                                w.Write("\tmlo\t"); w.Write(fe.Name); w.Write('\t'); w.Write(interior); w.Write('\n');
                                mlo++;
                            }
                        }
                }
                catch { errY++; }
            }
        }

        var mb = new FileInfo(outPath).Length / 1024.0 / 1024.0;
        Console.WriteLine("[*] ymap OK={0} errors={1}", okY, errY);
        Console.WriteLine("[+] {0}  ({1:0.0} MB)", outPath, mb);
        Console.WriteLine("[+] root={0}  mlo={1}  skipped={2}  total={3}  time={4:0.0} s",
            root, mlo, skipped, root + mlo, (DateTime.Now - t1).TotalSeconds);
    }
}
'@

# 'System.Collections'/'System.Runtime'/'System.Console' are REQUIRED: under PowerShell 7 (.NET 8+)
# these types are FORWARDED from netstandard; without a reference
# Add-Type crashes with "CS1069: type has been forwarded" / "CS0103: Console does not exist".
# Windows PowerShell 5.1 has no problem with it; PS7 fails every time.
$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[EntityIndexer]::Run($GtaFolder, $Out, $All.IsPresent)
