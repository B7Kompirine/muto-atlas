# build_ymap_lod.ps1 - indexes the LOD fields of ymap ROOT entities.
#
# WHY A SEPARATE INDEX: entities.tsv.gz / entities.db answer "WHERE is this object in
# the world", and they also expand MLO interiors into world coordinates, which
# inflates them (214 MB). The LOD question is entirely different: not a position but a CHAIN.
# Putting it into the same table would both break that pipeline and bloat it for nothing.
#
# CRITICAL: parentIndex points to the ORDER in the PARENT ymap's entity LIST
# (0-based). That is why every row stores 'idx' -- if the order is lost the
# chain cannot be resolved. For the same reason no entity is filtered; if any are
# dropped the indexes shift and the whole chain is read wrong.
#
# The chain crosses ymap FILES:  X.ymap -> X_lod.ymap -> X_slod.ymap
# The CodeWalker equivalent: the entity 'LOD Hierarchy' tab (ParentIndex +
# NumChildren). Details: skills/fivem-assets/trunk/flags.md
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_ymap_lod.ps1

param(
    [string]   $GtaFolder,
    [string]   $CodeWalker,
    [string[]] $ExtraFolders = @(),
    [string]   $Out
)

$ErrorActionPreference = 'Stop'

if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent) 'data' }
if (-not (Test-Path -LiteralPath $Out)) { New-Item -ItemType Directory -Path $Out | Out-Null }

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path -LiteralPath $CodeWalker)) {
    throw "CodeWalker.Core.dll not found. Pass it with -CodeWalker <path>."
}

$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V folder not found. Pass it with -GtaFolder <path>." }

$cwDir = Split-Path $CodeWalker -Parent
Write-Output "CodeWalker : $CodeWalker"
Write-Output "GTA V      : $GtaFolder"
Write-Output "Extra      : $(if($ExtraFolders.Count){$ExtraFolders -join '; '}else{'(none)'})"
Write-Output "Output     : $Out"

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
using CodeWalker.GameFiles;

public static class YmapLodIndexer
{
    static string F(float v) { return v.ToString("0.##", CultureInfo.InvariantCulture); }

    // In custom ymaps the archetype name is stored as a HASH; CodeWalker resolves it only
    // if it is in JenkIndex. We feed the model file names in the stream folder
    // -- a custom prop name is almost always the same as the file name.
    // (Same method as build_archetypes.ps1.)
    static void SeedNames(string folder, ref int seeded)
    {
        string[] exts = { "*.ydr", "*.yft", "*.ydd", "*.ytd" };
        foreach (var ext in exts)
        {
            string[] files;
            try { files = Directory.GetFiles(folder, ext, SearchOption.AllDirectories); }
            catch { continue; }
            foreach (var f in files)
            {
                var n = Path.GetFileNameWithoutExtension(f);
                if (string.IsNullOrEmpty(n)) continue;
                JenkIndex.Ensure(n.ToLowerInvariant());
                seeded++;
            }
        }
    }

    public static void Run(string gtaFolder, string[] extraFolders, string outFolder)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        var ymaps = new List<RpfFileEntry>();
        foreach (var rpf in man.AllRpfs)
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe != null && fe.NameLower.EndsWith(".ymap")) ymaps.Add(fe);
            }
        Console.WriteLine("[*] ymap entries: {0}", ymaps.Count);

        var t0 = DateTime.Now;
        long n = 0, nC = 0, chained = 0;
        int okY = 0, errY = 0, okC = 0, errC = 0;

        var outPath = Path.Combine(outFolder, "ymap_lod.tsv.gz");
        using (var fs = File.Create(outPath))
        using (var gz = new GZipStream(fs, CompressionLevel.Optimal))
        using (var w = new StreamWriter(gz))
        {
            // WITHOUT 'parentYmap' THE CHAIN CANNOT BE WALKED: parentIndex is an ORDER
            // number; which file's order it is, CMapData.parent in the ymap header
            // tells. Do not trust the file NAME pattern (X_lod.ymap) --
            // measured: only 456 of 8143 ymaps follow that pattern.
            // 'rpfPath' is REQUIRED: 4751 of 8252 ymap NAMES exist in more than one RPF
            // (base + DLC updates, up to 4 copies). If only the file name is
            // stored, the copies stack on top of each other, entity indexes get mixed up and
            // the chain looks WRONGLY "broken" -- measured: reading by name gave
            // 53,102 FALSE breaks.
            w.Write("ymap\tmapName\trpfPath\tparentYmap\tidx\tarchetype\tflags\tparentIndex\tnumChildren\tlodDist\tchildLodDist\tlodLevel\tpriority\n");

            foreach (var fe in ymaps)
            {
                try
                {
                    var data = fe.File.ExtractFile(fe);
                    if (data == null || data.Length == 0) { errY++; continue; }
                    var y = new YmapFile(); y.Load(data, fe);
                    okY++;

                    var ceds = y.CEntityDefs;
                    if (ceds == null) continue;

                    var par = y.CMapData.parent;
                    string parName = (par.Hash == 0) ? "" : par.ToString();
                    // 'mapName' is REQUIRED: CMapData.parent points not to the FILE NAME but to
                    // the ymap's INTERNAL NAME, and the two are not always the same.
                    // Measured: different in 177 of 3000 ymaps (5.9%) --
                    // example 'dt1_02_grass_0.ymap' -> internal name 'dt1_02'.
                    // If you match on the file name, the chain looks falsely broken.
                    string mapName = y.CMapData.name.ToString();

                    // ORDER = what parentIndex points to. NO filtering.
                    for (int i = 0; i < ceds.Length; i++)
                    {
                        var d = ceds[i];
                        w.Write(fe.Name);                    w.Write('\t');
                        w.Write(mapName);                    w.Write('\t');
                        w.Write(fe.Path);                    w.Write('\t');
                        w.Write(parName);                    w.Write('\t');
                        w.Write(i);                          w.Write('\t');
                        w.Write(d.archetypeName.ToString()); w.Write('\t');
                        w.Write(d.flags);                    w.Write('\t');
                        w.Write(d.parentIndex);              w.Write('\t');
                        w.Write(d.numChildren);              w.Write('\t');
                        w.Write(F(d.lodDist));               w.Write('\t');
                        w.Write(F(d.childLodDist));          w.Write('\t');
                        w.Write(d.lodLevel);                 w.Write('\t');
                        w.Write(d.priorityLevel);            w.Write('\n');
                        n++;
                        if (d.parentIndex >= 0 || d.numChildren > 0) chained++;
                    }
                }
                catch { errY++; }
            }

            // -- Custom (server resources, loose .ymap) ------------------
            // Names are fed AFTER THE VANILLA SCAN: RpfManager.Init
            // rebuilds JenkIndex and erases anything fed before.
            int seeded = 0;
            foreach (var f in extraFolders)
                if (Directory.Exists(f)) SeedNames(f, ref seeded);
            if (extraFolders.Length > 0)
                Console.WriteLine("[*] Custom model names fed to JenkIndex: {0}", seeded);

            foreach (var folder in extraFolders)
            {
                if (!Directory.Exists(folder)) { Console.WriteLine("[!] missing: {0}", folder); continue; }
                string[] files;
                try { files = Directory.GetFiles(folder, "*.ymap", SearchOption.AllDirectories); }
                catch { continue; }
                foreach (var f in files)
                {
                    try
                    {
                        var y = new YmapFile();
                        y.Load(File.ReadAllBytes(f));
                        okC++;
                        var ceds = y.CEntityDefs;
                        if (ceds == null) continue;

                        var par = y.CMapData.parent;
                        string parName = (par.Hash == 0) ? "" : par.ToString();
                        string mapName = y.CMapData.name.ToString();
                        string ymName = Path.GetFileName(f);

                        for (int i = 0; i < ceds.Length; i++)
                        {
                            var d = ceds[i];
                            w.Write(ymName);                     w.Write('\t');
                            w.Write(mapName);                    w.Write('\t');
                            w.Write(f);                          w.Write('\t');
                            w.Write(parName);                    w.Write('\t');
                            w.Write(i);                          w.Write('\t');
                            w.Write(d.archetypeName.ToString()); w.Write('\t');
                            w.Write(d.flags);                    w.Write('\t');
                            w.Write(d.parentIndex);              w.Write('\t');
                            w.Write(d.numChildren);              w.Write('\t');
                            w.Write(F(d.lodDist));               w.Write('\t');
                            w.Write(F(d.childLodDist));          w.Write('\t');
                            w.Write(d.lodLevel);                 w.Write('\t');
                            w.Write(d.priorityLevel);            w.Write('\n');
                            nC++;
                            if (d.parentIndex >= 0 || d.numChildren > 0) chained++;
                        }
                    }
                    catch { errC++; }
                }
            }
        }

        var mb = new FileInfo(outPath).Length / 1024.0 / 1024.0;
        Console.WriteLine("[+] {0}  ({1:0.0} MB)", outPath, mb);
        Console.WriteLine("[+] Vanilla : {0} ymap ({1} errors), {2} entities", okY, errY, n);
        if (extraFolders.Length > 0)
            Console.WriteLine("[+] Custom  : {0} ymap ({1} errors), {2} entities", okC, errC, nC);
        Console.WriteLine("[+] Total {0} entities, {1} of them in a LOD chain, {2:0.0} s",
                          n + nC, chained, (DateTime.Now - t0).TotalSeconds);
    }
}
'@

$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'mscorlib', 'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console',
          'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[YmapLodIndexer]::Run($GtaFolder, $ExtraFolders, $Out)
