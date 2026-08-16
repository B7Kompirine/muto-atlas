# extract_asset.ps1 — GTA V RPF arsivlerinden dosya cikarir.
#
# NEDEN: bir vanilla prop'u temel alip kendi modelimizi yapmak icin once
# .ydr/.yft/.ytd/.ycd dosyasini elde etmek gerekiyor. CodeWalker GUI'siyle
# tek tek aramak yerine ad/desen ile toplu cikarma.
#
# Kullanim:
#   powershell -File extract_asset.ps1 -Pattern "v_ilev_gb_*" -Out <klasor>
#   powershell -Command "& extract_asset.ps1 -Names @('a.ydr','b.yft') -Out <klasor>"
#   powershell -Command "& extract_asset.ps1 -Pattern 'head_000_r.ydd' -PathFilter 'mp_m_freemode_01' -Out <k>"
#
# -Names      : tam dosya adlari. DIKKAT: -File ile virgullu liste TEK STRING
#               olur ve sessizce hicbir sey bulunmaz -> -Command "& ... @('a','b')"
# -Pattern    : joker desen (ad uzerinde, uzanti dahil)
# -PathFilter : dosyanin ICINDE bulundugu RPF yolunda bu metin gecmeli.
#               NEDEN GEREKLI: ped bilesenleri her ped'de AYNI ADI tasir
#               (head_000_r.ydd, uppr_000_u.ydd...). Filtresiz cikarmada
#               onlarca ped ayni dosyaya yazar, sonuncusu kazanir ve hangi
#               ped'in mesh'i oldugu bilinmez. mp_m_freemode_01 kafasini
#               istiyorsan -PathFilter 'mp_m_freemode_01' sart.
# -Flatten    : $false ise cikti <Out>\<rpf yolu>\<ad> olarak yazilir; ayni
#               adli dosyalar birbirini EZMEZ.

param(
    [string[]] $Names = @(),
    [string]   $Pattern,
    [string]   $PathFilter,
    [bool]     $Flatten = $true,
    [Parameter(Mandatory=$true)][string] $Out,
    [string]   $GtaFolder,
    [string]   $CodeWalker
)

$ErrorActionPreference = 'Stop'

$CodeWalker = & "$PSScriptRoot\yol.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) { throw "CodeWalker.Core.dll bulunamadi." }

$GtaFolder = & "$PSScriptRoot\yol.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V klasoru bulunamadi." }

if (-not (Test-Path $Out)) { New-Item -ItemType Directory -Path $Out -Force | Out-Null }

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
using System.Collections.Generic;
using System.IO;
using CodeWalker.GameFiles;

public static class AssetExtractor
{
    public static void Run(string gtaFolder, string[] names, string pattern, string outFolder)
    { Run(gtaFolder, names, pattern, outFolder, null, true); }

    public static void Run(string gtaFolder, string[] names, string pattern, string outFolder,
                           string pathFilter, bool flatten)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        var want = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var n in names) if (!string.IsNullOrWhiteSpace(n)) want.Add(n.Trim());

        string pat = string.IsNullOrWhiteSpace(pattern) ? null : pattern.ToLowerInvariant();
        string pf = string.IsNullOrWhiteSpace(pathFilter) ? null : pathFilter.ToLowerInvariant();
        int found = 0;

        foreach (var rpf in man.AllRpfs)
        {
            // Ped bilesenleri her ped'de ayni adi tasir; hangi ped'den geldigini
            // bilmeden dogru mesh'i secmek imkansiz. Ped adi bazen RPF yolunda
            // (nested .rpf), bazen SADECE girdinin arsiv-ici yolunda gecer
            // (streamedpeds_mp.rpf icindeki klasor) -> IKISINE de bak.
            var rpfPath = (rpf.Path ?? "").Replace('\\', '/').ToLowerInvariant();
            bool rpfHit = pf != null && rpfPath.IndexOf(pf, StringComparison.Ordinal) >= 0;

            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null) continue;

                if (pf != null && !rpfHit)
                {
                    var ep = (fe.Path ?? "").Replace('\\', '/').ToLowerInvariant();
                    if (ep.IndexOf(pf, StringComparison.Ordinal) < 0) continue;
                }

                bool hit = want.Contains(fe.Name);
                if (!hit && pat != null) hit = Match(fe.NameLower, pat);
                if (!hit) continue;

                byte[] data;
                try { data = fe.File.ExtractFile(fe); }
                catch (Exception ex) { Console.WriteLine("[!] {0}: {1}", fe.Name, ex.Message); continue; }
                if (data == null || data.Length == 0) { Console.WriteLine("[!] {0}: bos", fe.Name); continue; }

                // RSC7 BASLIGINI GERI EKLE.
                // ExtractFile kaynak dosyanin (ydr/yft/ytd/ycd...) ic verisini
                // dondurur; 16 baytlik RSC7 basligi ayiklanmis olur. Sollumz /
                // OpenIV gibi araclar basligi bekler — basliksiz dosyaya
                // "Unsupported file format" der. CodeWalker'in kendi disa
                // aktarmasi da bu adimi yapiyor.
                // Diskteki gercek .ydr = RSC7 basligi + DEFLATE sikistirilmis govde.
                // Sadece baslik eklemek yetmiyor; Sollumz "DECOMPRESS_FAILED" veriyor.
                // Sira onemli: once sikistir, sonra basligi one ekle.
                var rrfe = fe as RpfResourceFileEntry;
                if (rrfe != null)
                {
                    try
                    {
                        data = ResourceBuilder.Compress(data);
                        data = ResourceBuilder.AddResourceHeader(rrfe, data);
                    }
                    catch (Exception ex) { Console.WriteLine("[!] {0}: baslik/sikistirma hatasi ({1})", fe.Name, ex.Message); }
                }

                string dst;
                if (flatten)
                {
                    dst = Path.Combine(outFolder, fe.Name);
                }
                else
                {
                    // Ayni adli dosyalar birbirini ezmesin: RPF yolunu klasore cevir.
                    var sub = (rpf.Path ?? "").Replace(':', '_');
                    foreach (var c in Path.GetInvalidPathChars()) sub = sub.Replace(c, '_');
                    var dir = Path.Combine(outFolder, sub);
                    Directory.CreateDirectory(dir);
                    dst = Path.Combine(dir, fe.Name);
                }
                File.WriteAllBytes(dst, data);
                Console.WriteLine("[+] {0,-38} {1,9:N0} bayt   (rpf: {2})", fe.Name, data.Length, rpf.Path);
                found++;
            }
        }

        Console.WriteLine("[=] {0} dosya cikarildi -> {1}", found, outFolder);
        if (found == 0) Console.WriteLine("[!] Hicbir sey bulunamadi. Ad/desen dogru mu?");
    }

    // Basit joker eslesme (* ve ?)
    static bool Match(string s, string p)
    {
        int si = 0, pi = 0, star = -1, mark = 0;
        while (si < s.Length)
        {
            if (pi < p.Length && (p[pi] == '?' || p[pi] == s[si])) { si++; pi++; }
            else if (pi < p.Length && p[pi] == '*') { star = pi++; mark = si; }
            else if (star >= 0) { pi = star + 1; si = ++mark; }
            else return false;
        }
        while (pi < p.Length && p[pi] == '*') pi++;
        return pi == p.Length;
    }
}
'@

# 'System.Collections' + 'System.Runtime' SART: PowerShell 7 / .NET 8+ altinda
# HashSet<> ve benzeri tipler netstandard'dan forward edilmis durumda ve
# referans verilmezse Add-Type "CS1069: type has been forwarded" ile coker.
$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'),
          'netstandard', 'System.Collections', 'System.Runtime', 'System.Linq',
          'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[AssetExtractor]::Run($GtaFolder, $Names, $Pattern, $Out, $PathFilter, $Flatten)
