# res_to_xml.ps1 — binary .ycd / .yed / .yft / .ydd / .ypt dosyasini XML'e dokur.
#
# NEDEN GEREKLI: Sollumz binary .ycd ve .yed OKUYAMAZ. Import denendiginde
# sessizce
#     "Binary resource format '.ycd' is not supported yet."
# uyarisi verip "Imported in 0.0 seconds" der — hata firlatmaz, sahneye de
# hicbir sey gelmez. Animasyonu Blender'da kare kare incelemek icin once
# XML'e cevirmek ZORUNLU.
#
# xml_to_ycd.ps1 bunun TERSIDIR (XML -> binary, oyuna hazir).
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File res_to_xml.ps1 -Path <dosya>
#   powershell -NoProfile -ExecutionPolicy Bypass -Command "& res_to_xml.ps1 -Path @('a.ycd','b.yed')"
#   powershell -NoProfile -ExecutionPolicy Bypass -File res_to_xml.ps1 -Dir <klasor> -Filter *.ycd
#
# Cikti: <ayni ad>.xml  (ya da -OutDir verilirse orada)

param(
    [string[]] $Path = @(),
    [string]   $Dir,
    [string]   $Filter = '*.ycd',
    [string]   $OutDir,
    [string]   $CodeWalker
)

$ErrorActionPreference = 'Stop'

if ($Dir) {
    if (-not (Test-Path -LiteralPath $Dir)) { throw "Klasor bulunamadi: $Dir" }
    $Path += (Get-ChildItem -LiteralPath $Dir -Filter $Filter -File | ForEach-Object { $_.FullName })
}
if ($Path.Count -eq 0) { throw "Dosya verilmedi. -Path veya -Dir kullan." }

$CodeWalker = & "$PSScriptRoot\yol.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) { throw "CodeWalker.Core.dll bulunamadi." }

$cwDir = Split-Path $CodeWalker -Parent
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
using System.IO;
using CodeWalker.GameFiles;

public static class ResToXml
{
    public static string One(string path, string outDir)
    {
        var data = File.ReadAllBytes(path);
        var name = Path.GetFileName(path);
        var ext  = Path.GetExtension(path).ToLowerInvariant();
        string xml = null;

        switch (ext)
        {
            case ".ycd":
            {
                var f = RpfFile.GetResourceFile<YcdFile>(data);
                f.Name = name;
                xml = YcdXml.GetXml(f);
                break;
            }
            case ".yed":
            {
                var f = RpfFile.GetResourceFile<YedFile>(data);
                f.Name = name;
                xml = YedXml.GetXml(f);
                break;
            }
            case ".yft":
            {
                var f = RpfFile.GetResourceFile<YftFile>(data);
                f.Name = name;
                xml = YftXml.GetXml(f);
                break;
            }
            case ".ydd":
            {
                var f = RpfFile.GetResourceFile<YddFile>(data);
                f.Name = name;
                xml = YddXml.GetXml(f);
                break;
            }
            case ".ydr":
            {
                var f = RpfFile.GetResourceFile<YdrFile>(data);
                f.Name = name;
                xml = YdrXml.GetXml(f);
                break;
            }
            case ".ybn":
            {
                var f = RpfFile.GetResourceFile<YbnFile>(data);
                f.Name = name;
                xml = YbnXml.GetXml(f);
                break;
            }
            case ".ytyp":
            {
                // DIKKAT: .ytyp bir Meta/PSO kaynagidir, RpfFile.GetResourceFile<YtypFile>
                // ile OKUNMAZ -> StackOverflowException ile coker. Kendi Load'u kullanilir
                // ve XML'i MetaXml uretir (YtypXml diye bir sinif YOKTUR).
                var f = new YtypFile();
                f.Load(data);
                string _fn;
                xml = MetaXml.GetXml(f, out _fn);
                break;
            }
            case ".ytd":
            {
                // Doku sozlugu. .ypt gibi: gomulu .dds'ler cikti klasorune AYRI
                // dosya olarak yazilir, geri derlerken ayni klasorde olmalidirlar.
                var f = RpfFile.GetResourceFile<YtdFile>(data);
                f.Name = name;
                var tdir = string.IsNullOrWhiteSpace(outDir) ? Path.GetDirectoryName(path) : outDir;
                if (!Directory.Exists(tdir)) Directory.CreateDirectory(tdir);
                xml = YtdXml.GetXml(f, tdir);
                break;
            }
            case ".ypt":
            {
                // Partikul efekti. Digerlerinden farki: gomulu .dds dokular
                // cikti klasorune AYRI dosya olarak yazilir; geri derlerken
                // (xml_to_res.ps1) o dosyalar XML ile ayni klasorde olmalidir.
                var f = RpfFile.GetResourceFile<YptFile>(data);
                f.Name = name;
                var texDir = string.IsNullOrWhiteSpace(outDir) ? Path.GetDirectoryName(path) : outDir;
                if (!Directory.Exists(texDir)) Directory.CreateDirectory(texDir);
                xml = YptXml.GetXml(f, texDir);
                break;
            }
            default:
                Console.WriteLine("[!] {0}: desteklenmeyen uzanti", name);
                return null;
        }

        if (string.IsNullOrEmpty(xml)) { Console.WriteLine("[!] {0}: XML bos", name); return null; }

        var dir = string.IsNullOrWhiteSpace(outDir) ? Path.GetDirectoryName(path) : outDir;
        if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
        var dst = Path.Combine(dir, name + ".xml");
        File.WriteAllText(dst, xml);
        Console.WriteLine("[+] {0,-52} -> {1:N0} bayt XML", name, xml.Length);
        return dst;
    }

    public static void Run(string[] paths, string outDir)
    {
        int ok = 0, bad = 0;
        foreach (var p in paths)
        {
            try { if (One(p, outDir) != null) ok++; else bad++; }
            catch (Exception ex) { Console.WriteLine("[!] {0}: {1}", Path.GetFileName(p), ex.Message); bad++; }
        }
        Console.WriteLine("[=] {0} basarili, {1} hatali", ok, bad);
    }
}
'@

# 'System.Collections'/'System.Runtime'/'System.Console' SART: PowerShell 7 (.NET 8+)
# altinda bu tipler netstandard'dan FORWARD edilmis durumda; referans verilmezse
# Add-Type "CS1069: type has been forwarded" / "CS0103: Console does not exist"
# ile coker. Windows PowerShell 5.1'de sorun cikmaz, PS7'de her seferinde cikar.
$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard', 'System.Xml',
          'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[ResToXml]::Run($Path, $OutDir)
