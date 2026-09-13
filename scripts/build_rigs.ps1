# build_rigs.ps1 - SKELETON (bone) and EXPRESSION (.yed) index.
#
# WHY:
#  - Animating props needs the bone NAME and TAG
#    (GetEntityBoneIndexByName, AttachEntityToEntity bone index, PlayEntityAnim).
#    Which prop has a bone and what it is called is written only in the .ydr/.yft skeleton.
#  - .yed = Expression Dictionary. Procedural bone motion (spring,
#    lookAt, reaction to collision) comes from here. What you call "playing an animation
#    with collision" is this layer.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_rigs.ps1 [-GtaFolder x] [-CodeWalker y] [-Out z]
#
# Output: data/skeletons.tsv.gz  and  data/expressions.tsv.gz

param(
    [string] $GtaFolder,
    [string] $CodeWalker,
    [string] $Out
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
using System.IO;
using System.IO.Compression;
using CodeWalker.GameFiles;

public static class RigIndexer
{
    static int WriteSkel(StreamWriter w, string model, string src, Skeleton sk)
    {
        if (sk == null) return 0;
        Bone[] bones = null;
        try { bones = sk.BonesSorted; } catch { }
        if (bones == null || bones.Length == 0) return 0;

        foreach (var b in bones)
        {
            if (b == null) continue;
            string nm = null;
            try { nm = b.Name; } catch { }
            if (string.IsNullOrEmpty(nm)) nm = "(unnamed)";
            int tag = 0, idx = 0, par = -1;
            try { tag = b.Tag; } catch { }
            try { idx = b.Index; } catch { }
            try { par = b.ParentIndex; } catch { }

            w.Write(model); w.Write('\t');
            w.Write(src); w.Write('\t');
            w.Write(bones.Length); w.Write('\t');
            w.Write(idx); w.Write('\t');
            w.Write(nm); w.Write('\t');
            w.Write(tag); w.Write('\t');
            w.Write(par); w.Write('\n');
        }
        return bones.Length;
    }

    public static void Run(string gtaFolder, string outFolder)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        var t0 = DateTime.Now;
        man.Init(gtaFolder, s => { }, s => { }, false, true);
        Console.WriteLine("[*] RPF scan: {0:0.0} s", (DateTime.Now - t0).TotalSeconds);

        var ydrs = new List<RpfFileEntry>();
        var yfts = new List<RpfFileEntry>();
        var yeds = new List<RpfFileEntry>();
        foreach (var rpf in man.AllRpfs)
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null) continue;
                if (fe.NameLower.EndsWith(".ydr")) ydrs.Add(fe);
                else if (fe.NameLower.EndsWith(".yft")) yfts.Add(fe);
                else if (fe.NameLower.EndsWith(".yed")) yeds.Add(fe);
            }
        Console.WriteLine("[*] ydr={0}  yft={1}  yed={2}", ydrs.Count, yfts.Count, yeds.Count);

        // -- SKELETONS ---------------------------------------------------
        var skelPath = Path.Combine(outFolder, "skeletons.tsv.gz");
        long rigged = 0, boneRows = 0;
        int scanned = 0, err = 0;
        var t1 = DateTime.Now;

        using (var fs = File.Create(skelPath))
        using (var gz = new GZipStream(fs, CompressionLevel.Optimal))
        using (var w = new StreamWriter(gz))
        {
            w.Write("model\tsrc\tboneCount\tboneIndex\tboneName\tboneTag\tparentIndex\n");

            foreach (var fe in ydrs)
            {
                scanned++;
                try
                {
                    var data = fe.File.ExtractFile(fe);
                    if (data == null || data.Length == 0) continue;
                    var y = new YdrFile(); y.Load(data, fe);
                    if (y.Drawable == null) continue;
                    int n = WriteSkel(w, Path.GetFileNameWithoutExtension(fe.Name), "ydr", y.Drawable.Skeleton);
                    if (n > 0) { rigged++; boneRows += n; }
                }
                catch { err++; }
                if (scanned % 20000 == 0)
                    Console.WriteLine("    ... {0} models scanned, {1} with a skeleton", scanned, rigged);
            }

            foreach (var fe in yfts)
            {
                scanned++;
                try
                {
                    var data = fe.File.ExtractFile(fe);
                    if (data == null || data.Length == 0) continue;
                    var y = new YftFile(); y.Load(data, fe);
                    if (y.Fragment == null || y.Fragment.Drawable == null) continue;
                    int n = WriteSkel(w, Path.GetFileNameWithoutExtension(fe.Name), "yft", y.Fragment.Drawable.Skeleton);
                    if (n > 0) { rigged++; boneRows += n; }
                }
                catch { err++; }
                if (scanned % 20000 == 0)
                    Console.WriteLine("    ... {0} models scanned, {1} with a skeleton", scanned, rigged);
            }
        }
        Console.WriteLine("[+] skeletons.tsv.gz  ({0:0.00} MB)  models with skeleton={1}  bone rows={2}  errors={3}  {4:0.0} s",
            new FileInfo(skelPath).Length / 1024.0 / 1024.0, rigged, boneRows, err, (DateTime.Now - t1).TotalSeconds);

        // -- EXPRESSION (.yed) -------------------------------------------
        var exprPath = Path.Combine(outFolder, "expressions.tsv.gz");
        long exprs = 0;
        int okY = 0, errY = 0;
        var t2 = DateTime.Now;

        using (var fs = File.Create(exprPath))
        using (var gz = new GZipStream(fs, CompressionLevel.Optimal))
        using (var w = new StreamWriter(gz))
        {
            w.Write("yed\texpression\thash\tstreams\ttracks\tsprings\n");

            foreach (var fe in yeds)
            {
                try
                {
                    var data = fe.File.ExtractFile(fe);
                    if (data == null || data.Length == 0) { errY++; continue; }
                    var y = new YedFile(); y.Load(data, fe);
                    okY++;
                    var map = y.ExprMap;
                    if (map == null) continue;
                    var dict = Path.GetFileNameWithoutExtension(fe.Name);
                    foreach (var kv in map)
                    {
                        var ex = kv.Value;
                        int st = 0, tr = 0, sp = 0;
                        try { st = ex.Streams.EntriesCount; } catch { }
                        try { tr = ex.Tracks.EntriesCount; } catch { }
                        try { sp = ex.Springs.EntriesCount; } catch { }
                        w.Write(dict); w.Write('\t');
                        w.Write(kv.Key.ToString()); w.Write('\t');
                        w.Write(kv.Key.Hash); w.Write('\t');
                        w.Write(st); w.Write('\t');
                        w.Write(tr); w.Write('\t');
                        w.Write(sp); w.Write('\n');
                        exprs++;
                    }
                }
                catch { errY++; }
            }
        }
        Console.WriteLine("[+] expressions.tsv.gz  yed={0} errors={1} expressions={2}  {3:0.0} s",
            okY, errY, exprs, (DateTime.Now - t2).TotalSeconds);
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

[RigIndexer]::Run($GtaFolder, $Out)
