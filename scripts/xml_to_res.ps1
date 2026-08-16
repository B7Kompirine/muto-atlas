# xml_to_res.ps1 — .yft.xml / .ydd.xml / .ydr.xml / .ybn.xml / .ypt.xml /
# .ytd.xml dosyasini oyuna hazir binary'ye cevirir. res_to_xml.ps1'in TERSIDIR.
#
# NEDEN GEREKLI: bir asset'i XML'e dokup elle duzeltip (or. bozuk bir dugumu
# cikarip) geri derlemek gerekebiliyor. Sollumz bunu yapamaz; CodeWalker.Core
# yapar ama GUI'siz cagrilmasi gerekir.
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File xml_to_res.ps1 -XmlPath <...>.yft.xml
#   powershell -NoProfile -ExecutionPolicy Bypass -File xml_to_res.ps1 -XmlPath <...>.ydd.xml -OutPath <...>.ydd

param(
    [Parameter(Mandatory=$true)][string] $XmlPath,
    [string] $OutPath,
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

# DIKKAT: yol icinde [peds] gibi kose parantez varsa Test-Path onu JOKER
# sanip dosyayi bulamaz -> -LiteralPath sart.
if (-not (Test-Path -LiteralPath $XmlPath)) { throw "XML bulunamadi: $XmlPath" }
if (-not $OutPath) { $OutPath = $XmlPath -replace '\.xml$', '' }

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
using System.Xml;
using CodeWalker.GameFiles;

public static class XmlToRes
{
    public static void Run(string xmlPath, string outPath)
    {
        var doc = new XmlDocument();
        doc.Load(xmlPath);

        string name = Path.GetFileName(outPath);
        string ext  = Path.GetExtension(outPath).ToLowerInvariant();
        byte[] data = null;

        switch (ext)
        {
            case ".yft":
            {
                var yft = XmlYft.GetYft(doc);
                if (yft == null) { Console.WriteLine("[!] XmlYft.GetYft null dondu."); return; }
                data = yft.Save();
                break;
            }
            case ".ydd":
            {
                var ydd = XmlYdd.GetYdd(doc);
                if (ydd == null) { Console.WriteLine("[!] XmlYdd.GetYdd null dondu."); return; }
                data = ydd.Save();
                break;
            }
            case ".ydr":
            {
                var ydr = XmlYdr.GetYdr(doc);
                if (ydr == null) { Console.WriteLine("[!] XmlYdr.GetYdr null dondu."); return; }
                data = ydr.Save();
                break;
            }
            case ".ybn":
            {
                var ybn = XmlYbn.GetYbn(doc);
                if (ybn == null) { Console.WriteLine("[!] XmlYbn.GetYbn null dondu."); return; }
                data = ybn.Save();
                break;
            }
            case ".ypt":
            {
                // Gomulu dokular (.dds) XML ile AYNI klasorde aranir; res_to_xml
                // onlari zaten oraya yazar. Klasor yanlissa doku sessizce dusmez,
                // XmlYpt null doner.
                var inputFolder = Path.GetDirectoryName(Path.GetFullPath(xmlPath));
                var ypt = XmlYpt.GetYpt(doc, inputFolder);
                if (ypt == null) { Console.WriteLine("[!] XmlYpt.GetYpt null dondu."); return; }
                data = ypt.Save();
                break;
            }
            case ".ytd":
            {
                // Doku sozlugu. .ypt gibi, <FileName> ile gosterilen .dds'ler
                // XML ile AYNI klasorde aranir.
                //
                // NEDEN GEREKLI: Sollumz bir drawable'a .ytd uretmeyi
                // atlayabiliyor (olculdu: uc drawable export edildi, yalnizca
                // birine .ytd yazildi; bilesen modelinin dokulari hicbir
                // sozluge girmedi ve oyunda dokusuz cikacakti). Elle .ytd
                // derlemek disinda telafisi yok.
                var ytdFolder = Path.GetDirectoryName(Path.GetFullPath(xmlPath));
                var ytd = XmlYtd.GetYtd(doc, ytdFolder);
                if (ytd == null) { Console.WriteLine("[!] XmlYtd.GetYtd null dondu."); return; }
                data = ytd.Save();
                break;
            }
            default:
                Console.WriteLine("[!] desteklenmeyen uzanti: " + ext);
                return;
        }

        File.WriteAllBytes(outPath, data);
        Console.WriteLine(string.Format("[+] {0,-42} -> {1:N0} bayt", name, data.Length));
    }
}
'@

$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'),
          'netstandard', 'System.Xml',
          # PowerShell 7 (.NET 8+) altinda bu tipler netstandard'dan forward
          # edilmistir; referans verilmezse Add-Type CS1069/CS0103 ile coker.
          # XmlDocument icin 'System.Xml' YETMEZ -> 'System.Xml.ReaderWriter'
          # gerekir. 'System.Private.Xml' EKLEME: ayni tipi o da tanimlar ve
          # CS0433 (type exists in both assemblies) hatasi verir.
          'System.Xml.ReaderWriter',
          'System.Collections', 'System.Runtime', 'System.Linq',
          'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[XmlToRes]::Run((Resolve-Path -LiteralPath $XmlPath).Path, $OutPath)
