# build_ptfx.ps1 - GTA V PARTICLE EFFECT CATALOG (.ypt files).
#
# WHY: ytyp_extensions.tsv.gz answers "which PROP uses which effect"
# but knows nothing about the effect ITSELF. "is there an effect called
# amb_steam_vent", "inside which .ypt", "how many emitters does it have" can
# only be answered by reading the .ypt files.
#
# A misspelt fxName is a SILENT failure (the effect never appears, no warning).
# This index is there to catch that failure before you write it.
#
# It also writes entityfx.tsv: the ytyp fxName is NOT an effect name but a TAG
# in entityfx.dat, whose row names the particle asset and the effect
# (AMB_WATER_ROOF_DRIPS_SHORT -> core / ent_amb_water_roof_drips_thin). Without
# this table 138 of 405 vanilla fxNames look like they point at nothing.
#
# .ypt STRUCTURE (a claim from a video, verified against the CodeWalker types):
#   ParticleEffectsList (root)
#     +- EffectRuleDictionary    <- effects; each one an EventEmitters list
#     +- EmitterRuleDictionary   <- emitter rules (spawn rate keyframes)
#     +- ParticleRuleDictionary  <- particle rules (color/size keyframes)
#     +- DrawableDictionary      <- models the effect uses
#     +- TextureDictionary       <- textures the effect uses
#   When building a custom effect all FIVE of these dictionaries move into the new .ypt.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_ptfx.ps1

param(
    [string] $GtaFolder,
    [string] $CodeWalker,
    [string] $Out
)

$ErrorActionPreference = 'Stop'

if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent) 'data' }
if (-not (Test-Path -LiteralPath $Out)) { New-Item -ItemType Directory -Path $Out | Out-Null }

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path -LiteralPath $CodeWalker)) { throw "CodeWalker.Core.dll not found." }
$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V folder not found." }

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
        var entityFx = new List<RpfFileEntry>();
        foreach (var rpf in man.AllRpfs)
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null) continue;
                if (fe.NameLower.EndsWith(".ypt")) ypts.Add(fe);
                else if (fe.NameLower == "entityfx.dat") entityFx.Add(fe);
            }
        Console.WriteLine("[*] ypt files: {0}", ypts.Count);

        var t0 = DateTime.Now;
        int okYpt = 0, err = 0;
        long nEffect = 0;
        string firstError = null;

        // the same effect name can occur in more than one ypt -> one row per name,
        // collecting the ypts it appears in
        var effects = new Dictionary<string, string[]>();     // name -> [ypt list, emitterCount]
        var yptEffects = new Dictionary<string, int>();

        foreach (var fe in ypts)
        {
            try
            {
                var data = fe.File.ExtractFile(fe);
                if (data == null || data.Length == 0) { err++; continue; }
                var f = new YptFile(); f.Load(data, fe);
                okYpt++;
                if (f.AllEffects == null) continue;
                yptEffects[fe.Name] = f.AllEffects.Length;

                foreach (var ef in f.AllEffects)
                {
                    if (ef == null) continue;
                    string name = (ef.Name == null) ? null : ef.Name.ToString();
                    if (string.IsNullOrEmpty(name)) continue;
                    nEffect++;
                    string[] existing;
                    if (effects.TryGetValue(name, out existing))
                    {
                        if (existing[0].Split(';').Length < 6 && existing[0].IndexOf(fe.Name) < 0)
                            existing[0] = existing[0] + ";" + fe.Name;
                    }
                    else
                    {
                        effects[name] = new string[] { fe.Name, ef.EventEmittersCount.ToString() };
                    }
                }
            }
            catch (Exception ex)
            {
                err++;
                if (firstError == null) firstError = fe.Name + " -> " + ex.GetType().Name + ": " + ex.Message;
            }
        }

        Console.WriteLine("[*] ypts read: {0}, errors: {1}", okYpt, err);
        if (firstError != null) Console.WriteLine("[!] first error: {0}", firstError);

        var sb = new StringBuilder(1 << 20);
        sb.Append("effect\teventEmitters\typts\n");
        foreach (var kv in effects)
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
        foreach (var kv in yptEffects) sb2.Append(Clean(kv.Key)).Append('\t').Append(kv.Value).Append('\n');
        // Under PS7 UTF8Encoding is forwarded to System.Text.Encoding.Extensions
        // (CS1069). Instead of adding a reference we write the bytes ourselves;
        // Encoding.UTF8.GetBytes writes NO BOM, the problem was only that
        // WriteAllText wants the encoder object.
        File.WriteAllBytes(Path.Combine(outFolder, "ptfx_files.tsv"),
                           Encoding.UTF8.GetBytes(sb2.ToString()));

        WriteEntityFx(entityFx, outFolder);

        Console.WriteLine("[+] ptfx_effects.tsv.gz  ({0} unique effects / {1} definitions)", effects.Count, nEffect);
        Console.WriteLine("[+] ptfx_files.tsv       ({0} ypt)", yptEffects.Count);
        Console.WriteLine("[+] {0:0.0} s", (DateTime.Now - t0).TotalSeconds);
    }

    // entityfx.dat is plain text: '#' comments, <BLOCK>_START / <BLOCK>_END markers,
    // and rows whose first three columns are TAG, PTFX_ASSET, FX_NAME. The base
    // copy is read first and the update copy last, so the update row wins.
    static void WriteEntityFx(List<RpfFileEntry> files, string outFolder)
    {
        files.Sort((a, b) => Rank(a).CompareTo(Rank(b)));
        var rows = new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase);
        int read = 0;
        foreach (var fe in files)
        {
            var data = fe.File.ExtractFile(fe);
            if (data == null || data.Length == 0)
                throw new Exception("entityfx.dat could not be read: " + fe.Path);
            read++;
            string block = null;
            foreach (var raw in Encoding.UTF8.GetString(data).Split('\n'))
            {
                var line = raw.Trim();
                if (line.Length == 0 || line[0] == '#') continue;
                if (line.EndsWith("_START")) { block = line.Substring(0, line.Length - 6); continue; }
                if (line.EndsWith("_END")) { block = null; continue; }
                if (block == null) continue;
                var p = line.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                if (p.Length < 3) continue;
                rows[p[0]] = new[] { p[0], block, p[1], p[2], fe.Path };
            }
        }
        if (read == 0) throw new Exception("no entityfx.dat found in the archives");

        var sb = new StringBuilder();
        sb.Append("tag\tblock\tasset\teffect\tsource\n");
        foreach (var r in rows.Values)
            sb.Append(Clean(r[0])).Append('\t').Append(Clean(r[1])).Append('\t')
              .Append(Clean(r[2])).Append('\t').Append(Clean(r[3])).Append('\t')
              .Append(Clean(r[4])).Append('\n');
        File.WriteAllBytes(Path.Combine(outFolder, "entityfx.tsv"), Encoding.UTF8.GetBytes(sb.ToString()));
        Console.WriteLine("[+] entityfx.tsv         ({0} tags from {1} entityfx.dat)", rows.Count, read);
    }

    static int Rank(RpfFileEntry fe)
    {
        string p = fe.Path.ToLowerInvariant();
        if (p.StartsWith("update\\update")) return 2;
        if (p.StartsWith("update")) return 1;
        return 0;
    }
}
'@

$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'mscorlib', 'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console',
          'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[PtfxIndexer]::Run($GtaFolder, $Out)
