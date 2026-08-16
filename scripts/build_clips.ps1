# build_clips.ps1 — .ycd (clip dictionary) dosyalarindan DETAYLI animasyon indeksi.
#
# Isim listesi (build_anims.py) "hangi animasyonlar var" sorusunu cevaplar.
# Bu script "hangisi TAM OLARAK dogru" sorusunu cevaplar:
#   • sure (saniye)          -> zamanlamayi tahmin etmeye gerek kalmaz
#   • tur (anim / animlist)  -> AnimationList = cok izli klip; prop + ped
#                               birlikte animasyonlu (senkron sahne) demek
#   • iz sayisi              -> kac ayri sey animasyonlaniyor
#   • root motion            -> karakter yer degistiriyor mu
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_clips.ps1 [-GtaFolder x] [-CodeWalker y] [-Out z]
#
# Cikti: data/clips.tsv.gz

param(
    [string] $GtaFolder,
    [string] $CodeWalker,
    [string] $Out
)

$ErrorActionPreference = 'Stop'

if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent) 'data' }
if (-not (Test-Path $Out)) { New-Item -ItemType Directory -Path $Out -Force | Out-Null }

$CodeWalker = & "$PSScriptRoot\yol.ps1" codewalker $CodeWalker
if (-not $CodeWalker) {
    # Son care: diskte ara. YAVAS (C:\ altini tarar). Kalicisi icin:
    #   python assetdb.py yol codewalker "<yol>"
    $CodeWalker = Get-ChildItem -Path "$env:USERPROFILE\Desktop","C:\" -Filter 'CodeWalker.Core.dll' `
                    -Recurse -Depth 4 -ErrorAction SilentlyContinue |
                  Select-Object -First 1 -ExpandProperty FullName
}
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) { throw "CodeWalker.Core.dll bulunamadi. -CodeWalker <yol> ile ver." }

$GtaFolder = & "$PSScriptRoot\yol.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V klasoru bulunamadi. -GtaFolder <yol> ile ver." }

$cwDir = Split-Path $CodeWalker -Parent
Write-Output "CodeWalker : $CodeWalker"
Write-Output "GTA V      : $GtaFolder"
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

public static class ClipIndexer
{
    static string F(float v) { return v.ToString("0.###", CultureInfo.InvariantCulture); }

    // Klip suresi ve iz sayisi: ClipAnimation tek animasyon, ClipAnimationList
    // birden fazla (ped + prop gibi) animasyonu bir arada tutar.
    // Kemik sayisi, ped animasyonu ile prop animasyonunu KESIN ayirir:
    // ped iskeleti ~30-90 kemik, prop tek kok kemik (1).
    static int Bones(Animation a)
    {
        if (a == null) return -1;
        try { return a.BoneIds.EntriesCount; } catch { return -1; }
    }

    static void Inspect(ClipBase cb, out string type, out int animCount, out float dur, out string bones)
    {
        type = "?"; animCount = 0; dur = 0f; bones = "";

        var ca = cb as ClipAnimation;
        if (ca != null)
        {
            type = "anim";
            animCount = 1;
            try { if (ca.Animation != null) { dur = ca.Animation.Duration; bones = Bones(ca.Animation).ToString(); } } catch { }
            if (dur <= 0f) { try { dur = ca.EndTime - ca.StartTime; } catch { } }
            return;
        }

        var cl = cb as ClipAnimationList;
        if (cl != null)
        {
            type = "animlist";
            try { animCount = cl.AnimationsCount1; } catch { }
            try { dur = cl.Duration; } catch { }
            try
            {
                var parts = new List<string>();
                foreach (var e in cl.Animations)
                {
                    if (e == null) { parts.Add("-1"); continue; }
                    parts.Add(Bones(e.Animation).ToString());
                }
                bones = string.Join(",", parts);
            }
            catch { }
        }
    }

    public static void Run(string gtaFolder, string outFolder)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        var t0 = DateTime.Now;
        man.Init(gtaFolder, s => { }, s => { }, false, true);
        Console.WriteLine("[*] RPF taramasi: {0:0.0} sn", (DateTime.Now - t0).TotalSeconds);

        var ycds = new List<RpfFileEntry>();
        foreach (var rpf in man.AllRpfs)
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe != null && fe.NameLower.EndsWith(".ycd")) ycds.Add(fe);
            }
        Console.WriteLine("[*] ycd girdisi: {0}", ycds.Count);

        var outPath = Path.Combine(outFolder, "clips.tsv.gz");
        long clips = 0, lists = 0;
        int ok = 0, err = 0;
        var t1 = DateTime.Now;

        using (var fs = File.Create(outPath))
        using (var gz = new GZipStream(fs, CompressionLevel.Optimal))
        using (var w = new StreamWriter(gz))
        {
            w.Write("dict\tclip\ttype\tanimCount\tduration\trootMotion\tbones\n");

            foreach (var fe in ycds)
            {
                try
                {
                    var data = fe.File.ExtractFile(fe);
                    if (data == null || data.Length == 0) { err++; continue; }
                    var y = new YcdFile();
                    y.Load(data, fe);
                    ok++;

                    var dict = Path.GetFileNameWithoutExtension(fe.Name);
                    var entries = y.ClipMapEntries;
                    if (entries == null) continue;

                    foreach (var cme in entries)
                    {
                        if (cme == null || cme.Clip == null) continue;
                        string type, bones; int ac; float dur;
                        Inspect(cme.Clip, out type, out ac, out dur, out bones);
                        if (type == "animlist") lists++;

                        string clipName = null;
                        try { clipName = cme.Clip.ShortName; } catch { }
                        if (string.IsNullOrEmpty(clipName)) { try { clipName = cme.Clip.Name; } catch { } }
                        if (string.IsNullOrEmpty(clipName)) clipName = cme.Hash.ToString();

                        // PlayTime bazen suresi ezilmis klipler icin daha dogru
                        float pt = 0f;
                        try { if (cme.OverridePlayTime) pt = cme.PlayTime; } catch { }
                        if (pt > 0f) dur = pt;

                        bool rm = false;
                        try { rm = cme.EnableRootMotion; } catch { }

                        w.Write(dict); w.Write('\t');
                        w.Write(clipName); w.Write('\t');
                        w.Write(type); w.Write('\t');
                        w.Write(ac); w.Write('\t');
                        w.Write(F(dur)); w.Write('\t');
                        w.Write(rm ? "1" : "0"); w.Write('\t');
                        w.Write(bones); w.Write('\n');
                        clips++;
                    }
                }
                catch { err++; }
            }
        }

        var mb = new FileInfo(outPath).Length / 1024.0 / 1024.0;
        Console.WriteLine("[*] ycd OK={0} hata={1}", ok, err);
        Console.WriteLine("[+] {0}  ({1:0.00} MB)", outPath, mb);
        Console.WriteLine("[+] klip={0}  cok-izli(animlist)={1}  sure={2:0.0} sn",
            clips, lists, (DateTime.Now - t1).TotalSeconds);
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

[ClipIndexer]::Run($GtaFolder, $Out)
