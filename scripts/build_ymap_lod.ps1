# build_ymap_lod.ps1 — ymap ROOT entity'lerinin LOD alanlarini indeksler.
#
# NEDEN AYRI INDEKS: entities.tsv.gz / entities.db "bu obje dunyada NEREDE"
# sorusuna cevap veriyor ve MLO ic mekanlarini da dunya koordinatina acarak
# sisiriyor (214 MB). LOD sorusu bambaska: konum degil, ZINCIR lazim.
# Ayni tabloya sokmak hem o hatti bozar hem gereksiz buyutur.
#
# KRITIK: parentIndex, UST ymap'in entity LISTESINDEKI SIRAYA isaret eder
# (0 tabanli). O yuzden her satirda 'idx' saklaniyor -- sira kaybolursa
# zincir cozulemez. Bu yuzden hicbir entity filtrelenmiyor; eleme yapilirsa
# indeksler kayar ve tum zincir yanlis okunur.
#
# Zincir ymap DOSYALARINI asar:  X.ymap -> X_lod.ymap -> X_slod.ymap
# CodeWalker'daki karsiligi: entity 'LOD Hierarchy' sekmesi (ParentIndex +
# NumChildren). Ayrinti: skills/fivem-assets/references/ytyp-ymap-bayraklari.md
#
# Kullanim:
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

if (-not $CodeWalker) {
    $cands = @(
        "$env:USERPROFILE\Desktop\FiveM\CodeWalker30_dev46\CodeWalker.Core.dll",
        "$env:USERPROFILE\Desktop\CodeWalker\CodeWalker.Core.dll"
    )
    $CodeWalker = $cands | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $CodeWalker -or -not (Test-Path -LiteralPath $CodeWalker)) {
    throw "CodeWalker.Core.dll bulunamadi. -CodeWalker <yol> ile ver."
}

if (-not $GtaFolder) {
    $cands = @(
        "C:\Program Files\Epic Games\GTAV",
        "C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V",
        "C:\Program Files\Rockstar Games\Grand Theft Auto V"
    )
    $GtaFolder = $cands | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $GtaFolder) { throw "GTA V klasoru bulunamadi. -GtaFolder <yol> ile ver." }

$cwDir = Split-Path $CodeWalker -Parent
Write-Output "CodeWalker : $CodeWalker"
Write-Output "GTA V      : $GtaFolder"
Write-Output "Ekstra     : $(if($ExtraFolders.Count){$ExtraFolders -join '; '}else{'(yok)'})"
Write-Output "Cikti      : $Out"

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

    // Custom ymap'lerde archetype adi HASH olarak durur; CodeWalker onu ancak
    // JenkIndex'te varsa cozer. Stream klasorundeki model dosya adlarini
    // besliyoruz -- custom prop adi neredeyse her zaman dosya adiyla ayni.
    // (build_archetypes.ps1 ile ayni yontem.)
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
        Console.WriteLine("[*] ymap girdisi: {0}", ymaps.Count);

        var t0 = DateTime.Now;
        long n = 0, nC = 0, zincirli = 0;
        int okY = 0, errY = 0, okC = 0, errC = 0;

        var outPath = Path.Combine(outFolder, "ymap_lod.tsv.gz");
        using (var fs = File.Create(outPath))
        using (var gz = new GZipStream(fs, CompressionLevel.Optimal))
        using (var w = new StreamWriter(gz))
        {
            // 'parentYmap' OLMADAN ZINCIR YURUNEMEZ: parentIndex bir SIRA
            // numarasidir, hangi dosyanin sirasi oldugunu ymap basligindaki
            // CMapData.parent soyler. Dosya ADI kalibina (X_lod.ymap) guvenme --
            // olculdu: 8143 ymap'in yalniz 456'si o kalibi tutuyor.
            // 'rpfPath' SART: 8252 ymap ADININ 4751'i birden cok RPF'te var
            // (base + DLC guncellemeleri, 4 kopyaya kadar). Yalniz dosya adi
            // saklanirsa kopyalar ust uste biner, entity indeksleri karisir ve
            // zincir YANLIS "kopuk" gorunur -- olculdu: ad bazli okumada
            // 53.102 SAHTE kopukluk cikti.
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
                    // 'mapName' SART: CMapData.parent DOSYA ADINA degil ymap'in
                    // IC ADINA isaret eder ve ikisi her zaman ayni degil.
                    // Olculdu: 3000 ymap'in 177'sinde (%5,9) farkli --
                    // ornek 'dt1_02_grass_0.ymap' -> ic ad 'dt1_02'.
                    // Dosya adiyla eslestirirsen zincir sahte kopuk gorunur.
                    string mapName = y.CMapData.name.ToString();

                    // SIRA = parentIndex'in isaret ettigi sey. Filtreleme YOK.
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
                        if (d.parentIndex >= 0 || d.numChildren > 0) zincirli++;
                    }
                }
                catch { errY++; }
            }

            // ── Custom (sunucu resource'lari, loose .ymap) ──────────
            // Adlar VANILLA TARAMASINDAN SONRA beslenir: RpfManager.Init
            // JenkIndex'i yeniden kuruyor ve once beslenenleri siliyor.
            int seeded = 0;
            foreach (var f in extraFolders)
                if (Directory.Exists(f)) SeedNames(f, ref seeded);
            if (extraFolders.Length > 0)
                Console.WriteLine("[*] JenkIndex'e beslenen custom model adi: {0}", seeded);

            foreach (var folder in extraFolders)
            {
                if (!Directory.Exists(folder)) { Console.WriteLine("[!] yok: {0}", folder); continue; }
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
                            if (d.parentIndex >= 0 || d.numChildren > 0) zincirli++;
                        }
                    }
                    catch { errC++; }
                }
            }
        }

        var mb = new FileInfo(outPath).Length / 1024.0 / 1024.0;
        Console.WriteLine("[+] {0}  ({1:0.0} MB)", outPath, mb);
        Console.WriteLine("[+] Vanilla : {0} ymap ({1} hata), {2} entity", okY, errY, n);
        if (extraFolders.Length > 0)
            Console.WriteLine("[+] Custom  : {0} ymap ({1} hata), {2} entity", okC, errC, nC);
        Console.WriteLine("[+] Toplam {0} entity, {1}'i LOD zincirinde, {2:0.0} sn",
                          n + nC, zincirli, (DateTime.Now - t0).TotalSeconds);
    }
}
'@

$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'mscorlib', 'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console',
          'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[YmapLodIndexer]::Run($GtaFolder, $ExtraFolders, $Out)
