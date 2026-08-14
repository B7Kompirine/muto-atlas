# build_entities.ps1 — ymap yerlesimlerinden DUNYA konumu indeksi uretir.
#
# Iki kaynak:
#   1) ymap root entity'leri            -> dogrudan dunya konumu
#   2) MLO instance + MLO archetype     -> ic mekan proplarinin dunya konumu
#      world = mloPos + rotate(localPos, mloRot)   [ham quaternion; dogrulandi]
#
# Dogrulama: v_ilev_gb_teldr @ Legion Square = (145.4186, -1041.8130, 29.6426)
# Bu, sunucudaki bagimsiz olcumle (145.4186, -1041.8125, 29.6426) ortusuyor.
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_entities.ps1 `
#       [-GtaFolder <yol>] [-CodeWalker <dll>] [-Out <data>] [-All]
#
# -All verilmezse LOD/SLOD ve arazi parcalari atlanir (indeks ~10x kucuk,
#  script yazarken lazim olan proplar korunur).
#
# Cikti: data/entities.tsv.gz

param(
    [string] $GtaFolder,
    [string] $CodeWalker,
    [string] $Out,
    [switch] $All
)

$ErrorActionPreference = 'Stop'

if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent) 'data' }
if (-not (Test-Path $Out)) { New-Item -ItemType Directory -Path $Out -Force | Out-Null }

if (-not $CodeWalker) {
    $cands = @(
        "$env:USERPROFILE\Desktop\FiveM\CodeWalker30_dev46\CodeWalker.Core.dll",
        "$env:USERPROFILE\Desktop\CodeWalker\CodeWalker.Core.dll"
    )
    $CodeWalker = $cands | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $CodeWalker) {
        $CodeWalker = Get-ChildItem -Path "$env:USERPROFILE\Desktop","C:\" -Filter 'CodeWalker.Core.dll' `
                        -Recurse -Depth 4 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
    }
}
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) { throw "CodeWalker.Core.dll bulunamadi. -CodeWalker <yol> ile ver." }

if (-not $GtaFolder) {
    $GtaFolder = @(
        'C:\Program Files\Epic Games\GTAV',
        'C:\Program Files\Rockstar Games\Grand Theft Auto V',
        'C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V',
        'C:\SteamLibrary\steamapps\common\Grand Theft Auto V'
    ) | Where-Object { Test-Path (Join-Path $_ 'GTA5.exe') } | Select-Object -First 1
}
if (-not $GtaFolder) { throw "GTA V klasoru bulunamadi. -GtaFolder <yol> ile ver." }

$cwDir = Split-Path $CodeWalker -Parent
Write-Output "CodeWalker : $CodeWalker"
Write-Output "GTA V      : $GtaFolder"
Write-Output "Mod        : $(if($All){'TUM entity'}else{'filtreli (LOD/arazi haric)'})"
Write-Output "Cikti      : $Out"

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

    // LOD / arazi / kaplama parcalari: script yazarken hicbir zaman
    // sorgulanmaz ama indeksin %90'ini kaplar.
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
        Console.WriteLine("[*] RPF taramasi: {0:0.0} sn", (DateTime.Now - t0).TotalSeconds);

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

        // ── 1) MLO archetype -> ic entity'lerin LOKAL konumlari ─────
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
        Console.WriteLine("[*] MLO archetype={0}  ic entity={1}", mloArch, mloEnt);

        // ── 2) ymap -> root entity + MLO instance genisletme ────────
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
                            // Ham quaternion dogru konvansiyon (bilinen koordinatla dogrulandi)
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
        Console.WriteLine("[*] ymap OK={0} hata={1}", okY, errY);
        Console.WriteLine("[+] {0}  ({1:0.0} MB)", outPath, mb);
        Console.WriteLine("[+] root={0}  mlo={1}  atlanan={2}  toplam={3}  sure={4:0.0} sn",
            root, mlo, skipped, root + mlo, (DateTime.Now - t1).TotalSeconds);
    }
}
'@

# 'System.Collections'/'System.Runtime'/'System.Console' SART: PowerShell 7 (.NET 8+)
# altinda bu tipler netstandard'dan FORWARD edilmis durumda; referans verilmezse
# Add-Type "CS1069: type has been forwarded" / "CS0103: Console does not exist"
# ile coker. Windows PowerShell 5.1'de sorun cikmaz, PS7'de her seferinde cikar.
$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[EntityIndexer]::Run($GtaFolder, $Out, $All.IsPresent)
