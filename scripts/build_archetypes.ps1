# build_archetypes.ps1 — GTA V RPF'lerinden ve custom kaynaklardan archetype indeksi uretir.
#
# Neden: bir prop/kapi/obje ile ilgili kod yazmadan ONCE "bu obje gercekten ne"
# sorusunun cevabi lazim. specialAttribute, flags, bbox (pivot), assetType ve
# fizik sozlugu bu sorunun cevabidir ve SADECE ytyp icinde vardir.
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_archetypes.ps1 `
#       [-GtaFolder <yol>] [-CodeWalker <CodeWalker.Core.dll>] `
#       [-ExtraFolders <resources yolu>[,<yol2>]] [-Out <data klasoru>]
#
# Cikti: data/archetypes.tsv.gz  +  data/assets.meta.json

param(
    [string]   $GtaFolder,
    [string]   $CodeWalker,
    [string[]] $ExtraFolders = @(),
    [string]   $Out
)

$ErrorActionPreference = 'Stop'

# ── Yol tespiti ─────────────────────────────────────────────────────
if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent) 'data' }
if (-not (Test-Path $Out)) { New-Item -ItemType Directory -Path $Out -Force | Out-Null }

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker) {
    # Son care: diskte ara. YAVAS (C:\ altini tarar). Kalicisi icin:
    #   python assetdb.py yol codewalker "<yol>"
    $CodeWalker = Get-ChildItem -Path "$env:USERPROFILE\Desktop","C:\" -Filter 'CodeWalker.Core.dll' `
                    -Recurse -Depth 4 -ErrorAction SilentlyContinue |
                  Select-Object -First 1 -ExpandProperty FullName
}
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) {
    throw "CodeWalker.Core.dll bulunamadi. -CodeWalker <yol> ile ver."
}

$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { Write-Warning "GTA V klasoru bulunamadi; sadece custom kaynaklar indekslenecek." }

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
    if (Test-Path $p) { return [System.Reflection.Assembly]::LoadFrom($p) }
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

public static class ArchetypeIndexer
{
    // ytyp'te archetype adi HASH olarak durur. Vanilla'da CodeWalker cozer;
    // custom kaynakta cozemez. O yuzden stream klasorundeki model dosya
    // adlarini (ydr/yft/ydd/ytd) JenkIndex'e besliyoruz — custom prop adi
    // neredeyse her zaman model dosya adiyla ayni.
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

    static string F(float v)
    {
        return v.ToString("0.####", CultureInfo.InvariantCulture);
    }

    static string Kind(Archetype a)
    {
        var t = a.GetType().Name;
        if (t.StartsWith("Mlo"))  return "mlo";
        if (t.StartsWith("Time")) return "time";
        return "base";
    }

    static void Row(StringBuilder sb, Archetype a, string src, string ytyp)
    {
        var d = a._BaseArchetypeDef;
        sb.Append(a.Name).Append('\t')
          .Append(d.name.Hash).Append('\t')
          .Append(src).Append('\t')
          .Append(ytyp).Append('\t')
          .Append(Kind(a)).Append('\t')
          .Append(d.assetType).Append('\t')
          .Append(d.specialAttribute).Append('\t')
          .Append(d.flags).Append('\t')
          .Append(F(d.lodDist)).Append('\t')
          .Append(F(d.bbMin.X)).Append(',').Append(F(d.bbMin.Y)).Append(',').Append(F(d.bbMin.Z)).Append('\t')
          .Append(F(d.bbMax.X)).Append(',').Append(F(d.bbMax.Y)).Append(',').Append(F(d.bbMax.Z)).Append('\t')
          .Append(F(d.bsRadius)).Append('\t')
          .Append(d.physicsDictionary).Append('\t')
          .Append(d.textureDictionary).Append('\t')
          .Append(d.clipDictionary).Append('\n');
    }

    public static void Run(string gtaFolder, string codeWalkerDll, string[] extraFolders, string outFolder)
    {
        var sb = new StringBuilder(1 << 24);
        sb.Append("name\thash\tsrc\tytyp\tkind\tassetType\tspecialAttribute\tflags\tlodDist\tbbMin\tbbMax\tbsRadius\tphysicsDict\ttextureDict\tclipDict\n");

        int vanillaYtyp = 0, vanillaArch = 0, customYtyp = 0, customArch = 0, errors = 0, seeded = 0;
        var t0 = DateTime.Now;

        // ── Vanilla RPF'ler ─────────────────────────────────────────
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
                    foreach (var a in y.AllArchetypes) { Row(sb, a, "vanilla", e.Name); vanillaArch++; }
                }
                catch { errors++; }
            }
            Console.WriteLine("[*] Vanilla: {0} ytyp / {1} archetype", vanillaYtyp, vanillaArch);
        }

        // ── Custom (sunucu resource'lari, loose .ytyp) ──────────────
        // Custom adlari VANILLA TARAMASINDAN SONRA beslenir: RpfManager.Init
        // JenkIndex'i yeniden kuruyor ve once beslenenleri siliyor.
        foreach (var f in extraFolders)
            if (Directory.Exists(f)) SeedNames(f, ref seeded);
        Console.WriteLine("[*] JenkIndex'e beslenen custom model adi: {0}", seeded);

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
                    foreach (var a in y.AllArchetypes) { Row(sb, a, "custom", Path.GetFileName(f)); customArch++; }
                }
                catch { errors++; }
            }
        }
        Console.WriteLine("[*] Custom: {0} ytyp / {1} archetype", customYtyp, customArch);

        // ── Yaz (gzip) ──────────────────────────────────────────────
        var outPath = Path.Combine(outFolder, "archetypes.tsv.gz");
        var raw = Encoding.UTF8.GetBytes(sb.ToString());
        using (var fs = File.Create(outPath))
        using (var gz = new GZipStream(fs, CompressionLevel.Optimal))
            gz.Write(raw, 0, raw.Length);

        var mb = new FileInfo(outPath).Length / 1024.0 / 1024.0;
        Console.WriteLine("[+] {0}  ({1:0.0} MB sikistirilmis / {2:0.0} MB ham)", outPath, mb, raw.Length / 1024.0 / 1024.0);

        var meta = new StringBuilder();
        meta.Append("{\n");
        meta.AppendFormat("  \"generatedAtUtc\": \"{0}\",\n", DateTime.UtcNow.ToString("o"));
        meta.AppendFormat("  \"gtaFolder\": {0},\n", Quote(gtaFolder));
        meta.AppendFormat("  \"codeWalker\": {0},\n", Quote(codeWalkerDll));
        meta.AppendFormat("  \"vanillaYtyp\": {0},\n  \"vanillaArchetypes\": {1},\n", vanillaYtyp, vanillaArch);
        meta.AppendFormat("  \"customYtyp\": {0},\n  \"customArchetypes\": {1},\n", customYtyp, customArch);
        meta.AppendFormat("  \"seededCustomNames\": {0},\n  \"errors\": {1},\n", seeded, errors);
        meta.AppendFormat("  \"buildSeconds\": {0}\n", ((DateTime.Now - t0).TotalSeconds).ToString("0.0", CultureInfo.InvariantCulture));
        meta.Append("}\n");
        File.WriteAllText(Path.Combine(outFolder, "assets.meta.json"), meta.ToString(), Encoding.UTF8);

        Console.WriteLine("[+] Toplam {0} archetype, {1:0.0} sn, {2} hata", vanillaArch + customArch, (DateTime.Now - t0).TotalSeconds, errors);
    }

    static string Quote(string s)
    {
        if (string.IsNullOrEmpty(s)) return "null";
        return "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
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

[ArchetypeIndexer]::Run($GtaFolder, $CodeWalker, $ExtraFolders, $Out)
