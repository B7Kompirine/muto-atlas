# build_extensions.ps1 — ytyp ARCHETYPE EXTENSION'larini indeksler.
#
# NEDEN AYRI BIR INDEKS: archetypes.tsv.gz archetype BASINA tek satir tutuyor;
# extension'lar ise archetype basina 0..N tane. Ayni tabloya sigmaz. Ayrica
# extension'lar bagimsiz sorulara cevap verir:
#
#   "hangi prop patlayinca toz cikarir"        -> Particle  (fxType=4)
#   "hangi proplarda expression var"            -> Expression (.yed zinciri)
#   "hangi prop cevresine ot uretir"            -> ProcObject
#   "bu kapinin door extension'i var mi"        -> Door
#
# Extension TIPLERI (14, CodeWalker.Core'da MCExtensionDef* siniflari;
# Sollumz 2.9 ytyp/properties/extensions.py ile birebir ayni liste):
#   ParticleEffect  AudioCollisionSettings  AudioEmitter  ExplosionEffect
#   Ladder  Buoyancy  LightShaft  SpawnPoint  SpawnPointOverride
#   WindDisturbance  ProcObject  Expression  Door  LightEffect
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_extensions.ps1 `
#       [-GtaFolder <yol>] [-CodeWalker <CodeWalker.Core.dll>] `
#       [-ExtraFolders @('<sunucu resources yolu>')] [-Out <data klasoru>]
#
# NOT: -ExtraFolders'i PowerShell'e -File ile gecerken dizi bozulur; virgullu
# liste TEK STRING olur. Dizi gerekiyorsa -Command "& script.ps1 -ExtraFolders @(...)".

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
    $found = $cands | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $found) {
        $found = Get-ChildItem -Path "$env:USERPROFILE\Desktop","C:\" -Filter 'CodeWalker.Core.dll' `
                 -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
    }
    $CodeWalker = $found
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

$cwDir = Split-Path $CodeWalker -Parent
Write-Output "CodeWalker : $CodeWalker"
Write-Output "GTA V      : $(if($GtaFolder){$GtaFolder}else{'(yok)'})"
Write-Output "Ekstra     : $(if($ExtraFolders.Count){$ExtraFolders -join '; '}else{'(yok)'})"
Write-Output "Cikti      : $Out"

# ── Calisma aninda bagimlilik cozumu ────────────────────────────────
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

public static class ExtensionIndexer
{
    static string F(float v) { return v.ToString("0.####", CultureInfo.InvariantCulture); }

    // Custom ytyp'te archetype adi ve Expression'in exprDict/expr alanlari HASH
    // olarak durur; CodeWalker onlari ancak JenkIndex'te varsa cozer.
    //
    // OLCULDU: bu adim ilk surumde YOKTU ve muto_depobox.ytyp'in 5 Expression'i
    // '2590473487' gibi cikti -- asset saglamdi, indeks korduo. '.yed' de
    // besleniyor cunku Expression extension'i sozluk adini oradan alir.
    static void SeedNames(string folder, ref int seeded)
    {
        string[] exts = { "*.ydr", "*.yft", "*.ydd", "*.ytd", "*.yed", "*.ycd", "*.ybn" };
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

    // NOT: SharpDX.Vector3'u PARAMETRE tipi yapma. Add-Type o zaman mscorlib
    // referansi ister (CS0012 'ValueType'). build_archetypes.ps1 de bu yuzden
    // alanlari satir ici kullaniyor.
    static string V3(float x, float y, float z) { return F(x) + "," + F(y) + "," + F(z); }

    static string H(MetaHash h)
    {
        // MetaHash.ToString() cozulebiliyorsa adi, cozulemiyorsa hash'i verir.
        var s = h.ToString();
        return string.IsNullOrEmpty(s) ? "0" : s;
    }

    static string Clean(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        return s.Replace('\t', ' ').Replace('\n', ' ').Replace('\r', ' ');
    }

    // Sutunlar: archetype src ytyp extType extName offsetPos
    //           fxName fxType boneTag scale probability extFlags detay
    static void Row(StringBuilder sb, string arch, string src, string ytyp,
                    string type, string name, string pos,
                    string fxName, string fxType, string boneTag,
                    string scale, string prob, string flags, string detay)
    {
        sb.Append(Clean(arch)).Append('\t')
          .Append(src).Append('\t')
          .Append(Clean(ytyp)).Append('\t')
          .Append(type).Append('\t')
          .Append(Clean(name)).Append('\t')
          .Append(pos).Append('\t')
          .Append(Clean(fxName)).Append('\t')
          .Append(fxType).Append('\t')
          .Append(boneTag).Append('\t')
          .Append(scale).Append('\t')
          .Append(prob).Append('\t')
          .Append(flags).Append('\t')
          .Append(Clean(detay)).Append('\n');
    }

    static void Emit(StringBuilder sb, Archetype a, string src, string ytyp, ref int n)
    {
        if (a == null || a.Extensions == null) return;

        foreach (var w in a.Extensions)
        {
            if (w == null) continue;
            string arch = a.Name;

            var pe = w as MCExtensionDefParticleEffect;
            if (pe != null)
            {
                var d = pe.Data;
                Row(sb, arch, src, ytyp, "Particle", H(d.name), V3(d.offsetPosition.X, d.offsetPosition.Y, d.offsetPosition.Z),
                    pe.fxName, d.fxType.ToString(), d.boneTag.ToString(),
                    F(d.scale), d.probability.ToString(), d.flags.ToString(),
                    "color=0x" + d.color.ToString("X8"));
                n++; continue;
            }

            var ex = w as MCExtensionDefExpression;
            if (ex != null)
            {
                var d = ex.Data;
                Row(sb, arch, src, ytyp, "Expression", H(d.name), V3(d.offsetPosition.X, d.offsetPosition.Y, d.offsetPosition.Z),
                    "", "", "", "", "", "",
                    "exprDict=" + H(d.expressionDictionaryName)
                    + ";expr=" + H(d.expressionName)
                    + ";creatureMeta=" + H(d.creatureMetadataName)
                    + ";onCollision=" + d.initialiseOnCollision.ToString());
                n++; continue;
            }

            var po = w as MCExtensionDefProcObject;
            if (po != null)
            {
                var d = po.Data;
                Row(sb, arch, src, ytyp, "ProcObject", H(d.name), V3(d.offsetPosition.X, d.offsetPosition.Y, d.offsetPosition.Z),
                    "", "", "", "", "", d.flags.ToString(),
                    "obj=" + d.objectHash.ToString()
                    + ";rIn=" + F(d.radiusInner) + ";rOut=" + F(d.radiusOuter)
                    + ";spacing=" + F(d.spacing)
                    + ";scale=" + F(d.minScale) + ".." + F(d.maxScale)
                    + ";scaleZ=" + F(d.minScaleZ) + ".." + F(d.maxScaleZ)
                    + ";zOff=" + F(d.minZOffset) + ".." + F(d.maxZOffset));
                n++; continue;
            }

            // Kalan 11 tip: alan semalari birbirinden cok farkli ve su an
            // sorgulanmiyor. Varliklarini kaydetmek yeter -- "bu archetype'ta
            // Ladder/Door/AudioEmitter var mi" sorusu boyle de cevaplanir.
            var tn = w.GetType().Name;
            if (tn.StartsWith("MCExtensionDef")) tn = tn.Substring("MCExtensionDef".Length);
            Row(sb, arch, src, ytyp, tn, Clean(w.Name), "", "", "", "", "", "", "", "");
            n++;
        }
    }

    public static void Run(string gtaFolder, string codeWalkerDll, string[] extraFolders, string outFolder)
    {
        var sb = new StringBuilder(1 << 22);
        sb.Append("archetype\tsrc\tytyp\textType\textName\toffsetPos\tfxName\tfxType\tboneTag\tscale\tprobability\textFlags\tdetay\n");

        int vanillaYtyp = 0, customYtyp = 0, nExt = 0, errors = 0;
        var t0 = DateTime.Now;

        if (!string.IsNullOrEmpty(gtaFolder))
        {
            GTA5Keys.LoadFromPath(gtaFolder, null);
            var man = new RpfManager();
            man.Init(gtaFolder, s => { }, s => { }, false, true);

            var entries = new List<RpfFileEntry>();
            foreach (var rpf in man.AllRpfs)
                foreach (var e in rpf.AllEntries)
                {
                    var fe = e as RpfFileEntry;
                    if (fe != null && fe.NameLower.EndsWith(".ytyp")) entries.Add(fe);
                }
            Console.WriteLine("[*] Vanilla ytyp girdisi: {0}", entries.Count);

            foreach (var e in entries)
            {
                try
                {
                    var data = e.File.ExtractFile(e);
                    if (data == null || data.Length == 0) { errors++; continue; }
                    var y = new YtypFile();
                    y.Load(data, e);
                    vanillaYtyp++;
                    if (y.AllArchetypes == null) continue;
                    foreach (var a in y.AllArchetypes) Emit(sb, a, "vanilla", e.Name, ref nExt);
                }
                catch { errors++; }
            }
            Console.WriteLine("[*] Vanilla: {0} ytyp, {1} extension", vanillaYtyp, nExt);
        }

        // Adlar VANILLA TARAMASINDAN SONRA beslenir: RpfManager.Init JenkIndex'i
        // yeniden kuruyor ve once beslenenleri siliyor.
        int seeded = 0;
        foreach (var f in extraFolders)
            if (Directory.Exists(f)) SeedNames(f, ref seeded);
        if (extraFolders.Length > 0)
            Console.WriteLine("[*] JenkIndex'e beslenen custom ad: {0}", seeded);

        foreach (var folder in extraFolders)
        {
            if (!Directory.Exists(folder)) { Console.WriteLine("[!] yok: {0}", folder); continue; }
            string[] files;
            try { files = Directory.GetFiles(folder, "*.ytyp", SearchOption.AllDirectories); }
            catch { continue; }
            foreach (var f in files)
            {
                try
                {
                    var data = File.ReadAllBytes(f);
                    var y = new YtypFile();
                    y.Load(data);
                    customYtyp++;
                    if (y.AllArchetypes == null) continue;
                    foreach (var a in y.AllArchetypes) Emit(sb, a, "custom", Path.GetFileName(f), ref nExt);
                }
                catch { errors++; }
            }
        }
        Console.WriteLine("[*] Custom: {0} ytyp", customYtyp);

        var outPath = Path.Combine(outFolder, "ytyp_extensions.tsv.gz");
        var raw = Encoding.UTF8.GetBytes(sb.ToString());
        using (var fs = File.Create(outPath))
        using (var gz = new GZipStream(fs, CompressionLevel.Optimal))
            gz.Write(raw, 0, raw.Length);

        Console.WriteLine("[+] {0}  ({1:0.0} KB sikistirilmis)", outPath, new FileInfo(outPath).Length / 1024.0);
        Console.WriteLine("[+] Toplam {0} extension, {1:0.0} sn, {2} hata",
                          nExt, (DateTime.Now - t0).TotalSeconds, errors);
    }
}
'@

# 'mscorlib' SART: bu betik struct'lari (MetaHash, SharpDX.Vector3) METOT
# PARAMETRESI olarak geciriyor; derleyici o zaman 'ValueType' tipini arar ve
# mscorlib referansi yoksa CS0012 ile coker. build_archetypes.ps1'de bu satir
# yok cunku orada struct'lar hep satir ici kullaniliyor, parametre yapilmiyor.
$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'mscorlib',
          'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[ExtensionIndexer]::Run($GtaFolder, $CodeWalker, $ExtraFolders, $Out)
