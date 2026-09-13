# extract_asset.ps1 - extracts files from the GTA V RPF archives.
#
# WHY: to build our own model on top of a vanilla prop we first need its
# .ydr/.yft/.ytd/.ycd file. Bulk extraction by name/pattern instead of searching
# one file at a time in the CodeWalker GUI.
#
# Usage:
#   powershell -File extract_asset.ps1 -Pattern "v_ilev_gb_*" -Out <folder>
#   powershell -Command "& extract_asset.ps1 -Names @('a.ydr','b.yft') -Out <folder>"
#   powershell -Command "& extract_asset.ps1 -Pattern 'head_000_r.ydd' -PathFilter 'mp_m_freemode_01' -Out <f>"
#
# -Names      : exact file names. CAREFUL: with -File a comma list becomes ONE STRING
#               and silently nothing is found -> -Command "& ... @('a','b')"
# -Pattern    : wildcard pattern (on the name, extension included)
# -PathFilter : this text must appear in the path of the RPF the file is INSIDE.
#               WHY IT IS NEEDED: ped components carry THE SAME NAME in every ped
#               (head_000_r.ydd, uppr_000_u.ydd...). Without the filter dozens of
#               peds write to the same file, the last one wins and you cannot tell
#               which ped the mesh belongs to. If you want the mp_m_freemode_01 head,
#               -PathFilter 'mp_m_freemode_01' is required.
# -Flatten    : if $false the output is written as <Out>\<rpf path>\<name>; files with
#               the same name do NOT overwrite each other.

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

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) { throw "CodeWalker.Core.dll not found." }

$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V folder not found." }

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
            // Ped components carry the same name in every ped; picking the right mesh without
            // knowing which ped it came from is impossible. The ped name is sometimes in the RPF path
            // (nested .rpf), sometimes ONLY in the entry's in-archive path
            // (a folder inside streamedpeds_mp.rpf) -> check BOTH.
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
                if (data == null || data.Length == 0) { Console.WriteLine("[!] {0}: empty", fe.Name); continue; }

                // ADD THE RSC7 HEADER BACK.
                // ExtractFile returns the inner data of the resource file (ydr/yft/ytd/ycd...);
                // the 16-byte RSC7 header is stripped. Tools such as Sollumz /
                // OpenIV expect the header - on a headerless file they say
                // "Unsupported file format". CodeWalker's own export
                // does this step too.
                // The real .ydr on disk = RSC7 header + DEFLATE-compressed body.
                // Adding only the header is not enough; Sollumz gives "DECOMPRESS_FAILED".
                // Order matters: compress first, then prepend the header.
                var rrfe = fe as RpfResourceFileEntry;
                if (rrfe != null)
                {
                    try
                    {
                        data = ResourceBuilder.Compress(data);
                        data = ResourceBuilder.AddResourceHeader(rrfe, data);
                    }
                    catch (Exception ex) { Console.WriteLine("[!] {0}: header/compression error ({1})", fe.Name, ex.Message); }
                }

                string dst;
                if (flatten)
                {
                    dst = Path.Combine(outFolder, fe.Name);
                }
                else
                {
                    // Keep same-named files from overwriting each other: turn the RPF path into a folder.
                    var sub = (rpf.Path ?? "").Replace(':', '_');
                    foreach (var c in Path.GetInvalidPathChars()) sub = sub.Replace(c, '_');
                    var dir = Path.Combine(outFolder, sub);
                    Directory.CreateDirectory(dir);
                    dst = Path.Combine(dir, fe.Name);
                }
                File.WriteAllBytes(dst, data);
                Console.WriteLine("[+] {0,-38} {1,9:N0} bytes   (rpf: {2})", fe.Name, data.Length, rpf.Path);
                found++;
            }
        }

        Console.WriteLine("[=] {0} files extracted -> {1}", found, outFolder);
        if (found == 0) Console.WriteLine("[!] Nothing found. Is the name/pattern right?");
    }

    // Simple wildcard match (* and ?)
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

# 'System.Collections' + 'System.Runtime' are REQUIRED: under PowerShell 7 / .NET 8+
# HashSet<> and similar types are forwarded from netstandard, and
# without a reference Add-Type crashes with "CS1069: type has been forwarded".
$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'),
          'netstandard', 'System.Collections', 'System.Runtime', 'System.Linq',
          'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[AssetExtractor]::Run($GtaFolder, $Names, $Pattern, $Out, $PathFilter, $Flatten)
