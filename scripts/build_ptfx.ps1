# build_ptfx.ps1 — GTA V PARTIKUL EFEKT KATALOGU (.ypt dosyalari).
#
# NEDEN: ytyp_extensions.tsv.gz "hangi PROP hangi efekti kullaniyor" sorusunu
# cevapliyor ama efektin KENDISI hakkinda hicbir sey bilmiyor. "amb_steam_vent
# diye bir efekt var mi", "hangi .ypt icinde", "kac emitter'i var" sorulari
# ancak .ypt'leri okuyarak cevaplanir.
#
# Yanlis yazilmis bir fxName SESSIZ hatadir (efekt hic cikmaz, uyari yok).
# Bu indeks o hatayi yazmadan once yakalamak icindir.
#
# .ypt YAPISI (video iddiasi CodeWalker tipleriyle dogrulandi):
#   ParticleEffectsList (kok)
#     +- EffectRuleDictionary    <- efektler; her biri EventEmitters listesi
#     +- EmitterRuleDictionary   <- emitter kurallari (spawn rate keyframe'leri)
#     +- ParticleRuleDictionary  <- particle kurallari (renk/boyut keyframe'leri)
#     +- DrawableDictionary      <- efektin kullandigi modeller
#     +- TextureDictionary       <- efektin kullandigi dokular
#   Ozel efekt uretirken bu BES sozlugun hepsi yeni .ypt'ye tasinir.
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_ptfx.ps1

param(
    [string] $GtaFolder,
    [string] $CodeWalker,
    [string] $Out
)

$ErrorActionPreference = 'Stop'

if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent) 'data' }
if (-not (Test-Path -LiteralPath $Out)) { New-Item -ItemType Directory -Path $Out | Out-Null }

$CodeWalker = & "$PSScriptRoot\yol.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path -LiteralPath $CodeWalker)) { throw "CodeWalker.Core.dll bulunamadi." }
$GtaFolder = & "$PSScriptRoot\yol.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V klasoru bulunamadi." }

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
using CodeWalker.GameFiles;

public static class PtfxIndexer
{
    static string Clean(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        return s.Replace('\t', ' ').Replace('\n', ' ').Replace('\r', ' ');
    }

    public static void Run(string gtaFolder, string outFolder)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        var ypts = new List<RpfFileEntry>();
        foreach (var rpf in man.AllRpfs)
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe != null && fe.NameLower.EndsWith(".ypt")) ypts.Add(fe);
            }
        Console.WriteLine("[*] ypt dosyasi: {0}", ypts.Count);

        var t0 = DateTime.Now;
        int okY = 0, err = 0;
        long nEffect = 0;
        string ilkHata = null;

        // ayni efekt adi birden cok ypt'de olabilir -> ad basina tek satir,
        // hangi ypt'lerde gectigi toplanir
        var efekt = new Dictionary<string, string[]>();     // ad -> [ypt listesi, emitterSayisi]
        var yptEfekt = new Dictionary<string, int>();

        foreach (var fe in ypts)
        {
            try
            {
                var data = fe.File.ExtractFile(fe);
                if (data == null || data.Length == 0) { err++; continue; }
                var f = new YptFile(); f.Load(data, fe);
                okY++;
                if (f.AllEffects == null) continue;
                yptEfekt[fe.Name] = f.AllEffects.Length;

                foreach (var ef in f.AllEffects)
                {
                    if (ef == null) continue;
                    string ad = (ef.Name == null) ? null : ef.Name.ToString();
                    if (string.IsNullOrEmpty(ad)) continue;
                    nEffect++;
                    string[] mevcut;
                    if (efekt.TryGetValue(ad, out mevcut))
                    {
                        if (mevcut[0].Split(';').Length < 6 && mevcut[0].IndexOf(fe.Name) < 0)
                            mevcut[0] = mevcut[0] + ";" + fe.Name;
                    }
                    else
                    {
                        efekt[ad] = new string[] { fe.Name, ef.EventEmittersCount.ToString() };
                    }
                }
            }
            catch (Exception ex)
            {
                err++;
                if (ilkHata == null) ilkHata = fe.Name + " -> " + ex.GetType().Name + ": " + ex.Message;
            }
        }

        Console.WriteLine("[*] okunan ypt: {0}, hata: {1}", okY, err);
        if (ilkHata != null) Console.WriteLine("[!] ilk hata: {0}", ilkHata);

        var sb = new StringBuilder(1 << 20);
        sb.Append("effect\teventEmitters\typts\n");
        foreach (var kv in efekt)
            sb.Append(Clean(kv.Key)).Append('\t')
              .Append(kv.Value[1]).Append('\t')
              .Append(Clean(kv.Value[0])).Append('\n');

        var outPath = Path.Combine(outFolder, "ptfx_effects.tsv.gz");
        var raw = Encoding.UTF8.GetBytes(sb.ToString());
        using (var fs = File.Create(outPath))
        using (var gz = new GZipStream(fs, CompressionLevel.Optimal))
            gz.Write(raw, 0, raw.Length);

        var sb2 = new StringBuilder();
        sb2.Append("ypt\teffectCount\n");
        foreach (var kv in yptEfekt) sb2.Append(Clean(kv.Key)).Append('\t').Append(kv.Value).Append('\n');
        // UTF8Encoding PS7 altinda System.Text.Encoding.Extensions'a forward
        // edilmis (CS1069). Referans eklemek yerine bayti kendimiz yaziyoruz;
        // Encoding.UTF8.GetBytes BOM URETMEZ, sorun yalniz WriteAllText'in
        // encoder nesnesini istemesindeydi.
        File.WriteAllBytes(Path.Combine(outFolder, "ptfx_files.tsv"),
                           Encoding.UTF8.GetBytes(sb2.ToString()));

        Console.WriteLine("[+] ptfx_effects.tsv.gz  ({0} benzersiz efekt / {1} tanim)", efekt.Count, nEffect);
        Console.WriteLine("[+] ptfx_files.tsv       ({0} ypt)", yptEfekt.Count);
        Console.WriteLine("[+] {0:0.0} sn", (DateTime.Now - t0).TotalSeconds);
    }
}
'@

$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'mscorlib', 'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console',
          'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[PtfxIndexer]::Run($GtaFolder, $Out)
