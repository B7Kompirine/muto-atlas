# xml_to_ycd.ps1 — Sollumz'un urettigi .ycd.xml dosyasini oyuna hazir
# binary .ycd'ye cevirir.
#
# NEDEN GEREKLI: .ycd, Sollumz'un format saglayici sisteminin DISINDADIR.
# O sistem (szio.gta5) yalnizca su 8 uzantiyi tanir:
#   .ybn .ydr .ydd .yft .yld .ytyp .ymap .ytd
# Clip dictionary export'u ise ycd/ycdexport.py icinde dogrudan
# clip_dict.write_xml(filepath) cagirir -- target_formats ayarina HIC
# bakmaz. Yani 'NATIVE' secmek .ycd icin bir sey degistirmez; script
# "Successfully exported" der ama klasorde .ycd yerine .ycd.xml olur.
# Sessiz bir tuzak; dosya yok saniyorsun.
#
# NOT: Diger 8 uzanti icin 'NATIVE' GERCEKTEN binary uretir -- ama yalnizca
# 'pymateria' paketi kuruluysa. Kurulu degilse Sollumz target_formats'i
# sessizce {'CWXML'}'e dusurur (sollumz_preferences.py:377).
#
# Kullanim:
#   powershell -File xml_to_ycd.ps1 -XmlPath <...>\muto_vauldr_anim.ycd.xml

param(
    [Parameter(Mandatory=$true)][string] $XmlPath,
    [string] $OutPath,
    # Klip adi — hash bundan hesaplanir. ClipBase.Name OKUMAK
    # NotImplementedException firlatiyor, o yuzden disaridan veriyoruz.
    [string[]] $ClipName = @(),
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

# DIKKAT: yol icinde [script] gibi kose parantez varsa Test-Path onu
# JOKER sanip dosyayi bulamaz. -LiteralPath sart.
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

public static class XmlToYcd
{
    public static uint Joaat(string s)
    {
        uint h = 0; s = s.ToLowerInvariant();
        for (int i = 0; i < s.Length; i++) { h += (byte)s[i]; h += h << 10; h ^= h >> 6; }
        h += h << 3; h ^= h >> 11; h += h << 15; return h;
    }

    public static void Run(string xmlPath, string outPath, string[] clipNames)
    {
        var doc = new XmlDocument();
        doc.Load(xmlPath);

        var ycd = XmlYcd.GetYcd(doc);
        if (ycd == null) { Console.WriteLine("[!] XmlYcd.GetYcd null dondu."); return; }

        // Ic yapiyi rapor et: klip/animasyon sayisi sifirsa export bostur.
        int clips = 0, anims = 0;
        try { if (ycd.ClipMap != null)      clips = ycd.ClipMap.Count; } catch { }
        try { if (ycd.AnimMap != null)      anims = ycd.AnimMap.Count; } catch { }
        Console.WriteLine("[*] klip={0}  animasyon={1}", clips, anims);

        // ── AD HASH'LERINI ELLE YAZ ─────────────────────────────────
        // XmlYcd.GetYcd klip adini koyuyor ama HASH'ini hesaplamiyor;
        // Save() hash=0 yaziyor ve oyun klibi HASH'ten aradigi icin
        // PlayEntityAnim false donuyor.
        // Clip.Name OKUMAK NotImplementedException firlatiyor -> adi
        // disaridan -ClipName ile aliyoruz, hic okumuyoruz.
        // OLCULDU: Sollumz'un Type="Animation" (tek animasyonlu) klip yazdigi
        // XML'lerde bu dongu StackOverflowException ile COKUYOR. Ustelik o
        // durumda Sollumz <Name>pack:/klip</Name> alanini ZATEN yaziyor, yani
        // elle hash atamaya gerek yok. Bu yuzden:
        //   * -ClipName verilmediyse dokunma (normal yol),
        //   * verildiyse de coksun diye butun blogu korumaya al.
        if (clipNames != null && clipNames.Length > 0 &&
            ycd.ClipDictionary != null && ycd.ClipDictionary.Clips != null)
        {
          try {
            // Clips duz dizi degil (ResourcePointerArray) -> Length yok, foreach.
            int i = 0;
            foreach (var ce in ycd.ClipDictionary.Clips)
            {
                if (ce == null || i >= clipNames.Length) { i++; continue; }
                var nm = clipNames[i];
                if (nm.StartsWith("pack:/")) nm = nm.Substring(6);
                ce.Hash = new MetaHash(Joaat(nm));
                Console.WriteLine("    klip[{0}] '{1}' -> hash {2}", i, nm, Joaat(nm));
                i++;
            }
          }
          catch (Exception ex)
          {
              Console.WriteLine("[!] klip hash atlanildi ({0}). XML'de <Name> zaten",
                                ex.GetType().Name);
              Console.WriteLine("    varsa buna gerek yok; -ClipName vermeden calistir.");
          }
        }

        byte[] data = ycd.Save();
        File.WriteAllBytes(outPath, data);
        Console.WriteLine("[+] yazildi: {0}  ({1:N0} bayt)", outPath, data.Length);

        // Geri oku ve dogrula
        var chk = RpfFile.GetResourceFile<YcdFile>(File.ReadAllBytes(outPath));
        int n = 0;
        try { if (chk != null && chk.ClipMap != null) n = chk.ClipMap.Count; } catch { }
        Console.WriteLine(n > 0
            ? string.Format("[+] dogrulama tamam: {0} klip geri okundu", n)
            : "[X] DOGRULAMA HATASI: geri okumada klip yok");
    }
}
'@

# 'System.Collections'/'System.Runtime'/'System.Console' SART: PowerShell 7 (.NET 8+)
# altinda bu tipler netstandard'dan FORWARD edilmis durumda; referans verilmezse
# Add-Type "CS1069: type has been forwarded" / "CS0103: Console does not exist"
# ile coker. Windows PowerShell 5.1'de sorun cikmaz, PS7'de her seferinde cikar.
# XmlDocument icin 'System.Xml' YETMEZ (PS7/.NET8+): tip
# 'System.Xml.ReaderWriter'a forward edilmistir. 'System.Private.Xml'
# EKLEME - ayni tipi o da tanimlar, CS0433 verir.
$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard', 'System.Xml',
          'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions', 'System.Xml.ReaderWriter')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[XmlToYcd]::Run($XmlPath, $OutPath, $ClipName)
