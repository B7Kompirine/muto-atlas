# build_lights.ps1 — GTA V GOMULU ISIK KATALOGU (.ydr / .yft / .ydd).
#
# NEDEN: isik parametreleri sihirli sayilarla dolu. `TimeFlags = 15728703` bir
# sayi degil, "saat 20'den 06'ya kadar yanar" demektir; `Flags = 384` bir bit
# kumesidir. Bu degerleri baska bir proptan kopyalayip gecmek en sik yapilan
# hatadir -- isik yanlis saatte yanar, ya da hic yanmaz, ve sebep dosyaya
# bakinca gorunmez.
#
# Bu indeks "vanilla ne yapiyor" sorusunu OLCUMLE cevaplar:
#     assetdb.py light --tablo
# Bir deger araligin disindaysa bu HATA demek degildir; "vanilla'da gormedim"
# demektir. Fark onemli.
#
# ISIK NEREDE DURUYOR (CodeWalker.Core uzerinde reflection ile dogrulandi):
#   .ydr -> YdrFile.Drawable.LightAttributes            (Drawable)
#   .yft -> YftFile.Fragment.LightAttributes            (FragType -- DIKKAT:
#           Fragment.Drawable DEGIL; o FragDrawable'dir ve DrawableBase'ten
#           turer, LightAttributes TASIMAZ.)
#   .ydd -> YddFile.Drawables[i].LightAttributes        (sozlukteki her drawable)
# Ayni ayrim XML'de de gorunur: <Fragment><Lights> vardir,
# <Fragment><Drawable><Lights> YOKTUR.
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_lights.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_lights.ps1 -Ornek 400

param(
    [string] $GtaFolder,
    [string] $CodeWalker,
    [string] $Out,
    [int]    $Ornek = 0      # >0 ise orneklem modu (hiz olcumu icin)
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

public static class LightIndexer
{
    static string Clean(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        return s.Replace('\t', ' ').Replace('\n', ' ').Replace('\r', ' ');
    }

    static string F(float v)
    {
        return v.ToString("0.####", CultureInfo.InvariantCulture);
    }

    static void Satir(StringBuilder sb, string model, string ext, int idx, LightAttributes L)
    {
        sb.Append(Clean(model)).Append('\t')
          .Append(ext).Append('\t')
          .Append(idx).Append('\t')
          .Append(L.Type.ToString()).Append('\t')
          .Append(L.ColorR).Append(',').Append(L.ColorG).Append(',').Append(L.ColorB).Append('\t')
          .Append(F(L.Intensity)).Append('\t')
          .Append(F(L.Falloff)).Append('\t')
          .Append(F(L.FalloffExponent)).Append('\t')
          .Append(F(L.ConeInnerAngle)).Append('\t')
          .Append(F(L.ConeOuterAngle)).Append('\t')
          .Append(F(L.CoronaSize)).Append('\t')
          .Append(F(L.CoronaIntensity)).Append('\t')
          .Append(F(L.VolumeIntensity)).Append('\t')
          .Append(F(L.VolumeSizeScale)).Append('\t')
          .Append(L.Flags).Append('\t')
          .Append(L.TimeFlags).Append('\t')
          .Append(L.BoneId).Append('\t')
          .Append(L.GroupId).Append('\t')
          .Append(L.Flashiness).Append('\t')
          .Append(L.ShadowBlur).Append('\t')
          .Append(F(L.ShadowNearClip)).Append('\t')
          .Append(L.ProjectedTextureHash.ToString()).Append('\n');
    }

    static int Yaz(StringBuilder sb, string model, string ext,
                   ResourceSimpleList64<LightAttributes> list)
    {
        if (list == null) return 0;
        var it = list.data_items;
        if (it == null || it.Length == 0) return 0;
        for (int i = 0; i < it.Length; i++) Satir(sb, model, ext, i, it[i]);
        return it.Length;
    }

    public static void Run(string gtaFolder, string outFolder, int ornek)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        var hedef = new List<RpfFileEntry>();
        foreach (var rpf in man.AllRpfs)
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null) continue;
                var n = fe.NameLower;
                if (n.EndsWith(".ydr") || n.EndsWith(".yft") || n.EndsWith(".ydd")) hedef.Add(fe);
            }
        Console.WriteLine("[*] taranacak dosya: {0}", hedef.Count);

        int adim = 1;
        if (ornek > 0 && hedef.Count > ornek) adim = hedef.Count / ornek;

        var sb = new StringBuilder(1 << 22);
        sb.Append("model\text\tidx\ttype\tcolour\tintensity\tfalloff\tfalloffExp\t");
        sb.Append("coneInner\tconeOuter\tcoronaSize\tcoronaIntensity\tvolumeIntensity\t");
        sb.Append("volumeSizeScale\tflags\ttimeFlags\tboneId\tgroupId\tflashiness\t");
        sb.Append("shadowBlur\tshadowNearClip\tprojTex\n");

        var t0 = DateTime.Now;
        int okunan = 0, hata = 0, isikliDosya = 0;
        long nIsik = 0;
        string ilkHata = null;

        for (int i = 0; i < hedef.Count; i += adim)
        {
            var fe = hedef[i];
            try
            {
                var data = fe.File.ExtractFile(fe);
                if (data == null || data.Length == 0) { hata++; continue; }
                var n = fe.NameLower;
                string model = fe.Name;
                int k = model.LastIndexOf('.');
                if (k > 0) model = model.Substring(0, k);
                int bulunan = 0;

                if (n.EndsWith(".ydr"))
                {
                    var f = new YdrFile(); f.Load(data, fe); okunan++;
                    if (f.Drawable != null) bulunan = Yaz(sb, model, "ydr", f.Drawable.LightAttributes);
                }
                else if (n.EndsWith(".yft"))
                {
                    var f = new YftFile(); f.Load(data, fe); okunan++;
                    // DIKKAT: Fragment.LightAttributes -- Fragment.Drawable DEGIL.
                    if (f.Fragment != null) bulunan = Yaz(sb, model, "yft", f.Fragment.LightAttributes);
                }
                else
                {
                    var f = new YddFile(); f.Load(data, fe); okunan++;
                    if (f.Drawables != null)
                        for (int d = 0; d < f.Drawables.Length; d++)
                        {
                            var dr = f.Drawables[d];
                            if (dr == null) continue;
                            string ad = (dr.Name == null) ? model : dr.Name;
                            bulunan += Yaz(sb, ad, "ydd", dr.LightAttributes);
                        }
                }

                if (bulunan > 0) { isikliDosya++; nIsik += bulunan; }
            }
            catch (Exception ex)
            {
                hata++;
                if (ilkHata == null) ilkHata = fe.Name + ": " + ex.Message;
            }

            if (okunan > 0 && okunan % 20000 == 0)
                Console.WriteLine("    ... {0} dosya, {1} isik, {2:0} sn",
                                  okunan, nIsik, (DateTime.Now - t0).TotalSeconds);
        }

        Console.WriteLine("[*] okunan: {0}, hata: {1}", okunan, hata);
        if (ilkHata != null) Console.WriteLine("[!] ilk hata: {0}", ilkHata);
        Console.WriteLine("[*] isikli dosya: {0} ({1:0.00}%)  toplam isik: {2}",
                          isikliDosya, 100.0 * isikliDosya / Math.Max(1, okunan), nIsik);

        if (ornek > 0)
        {
            double sn = (DateTime.Now - t0).TotalSeconds;
            Console.WriteLine("[*] ORNEKLEM: {0:0.0} sn / {1} dosya -> tam tarama tahmini {2:0.0} dk",
                              sn, okunan, (sn / Math.Max(1, okunan)) * hedef.Count / 60.0);
            return;   // orneklem modunda DOSYA YAZILMAZ (yarim veri kalici olmasin)
        }

        var outPath = Path.Combine(outFolder, "lights.tsv.gz");
        var raw = Encoding.UTF8.GetBytes(sb.ToString());
        using (var fs = File.Create(outPath))
        using (var gz = new GZipStream(fs, CompressionLevel.Optimal))
            gz.Write(raw, 0, raw.Length);

        Console.WriteLine("[+] lights.tsv.gz  ({0} isik / {1} dosya)", nIsik, isikliDosya);
        Console.WriteLine("[+] {0:0.0} sn", (DateTime.Now - t0).TotalSeconds);
    }
}
'@

$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'mscorlib', 'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console',
          'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[LightIndexer]::Run($GtaFolder, $Out, $Ornek)
