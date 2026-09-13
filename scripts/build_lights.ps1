# build_lights.ps1 - GTA V EMBEDDED LIGHT CATALOG (.ydr / .yft / .ydd).
#
# WHY: light parameters are full of magic numbers. `TimeFlags = 15728703` is not a
# number, it means "on from 20:00 to 06:00"; `Flags = 384` is a bit
# set. Copying these values from another prop and moving on is the most common
# mistake -- the light turns on at the wrong hour, or never, and the reason is not
# visible when you look at the file.
#
# This index answers "what does vanilla do" with MEASUREMENT:
#     assetdb.py light --table
# A value outside the range does not mean it is WRONG; it means "I have not seen it
# in vanilla". The difference matters.
#
# WHERE THE LIGHT LIVES (verified by reflection on CodeWalker.Core):
#   .ydr -> YdrFile.Drawable.LightAttributes            (Drawable)
#   .yft -> YftFile.Fragment.LightAttributes            (FragType -- CAREFUL:
#           NOT Fragment.Drawable; that is a FragDrawable, derived from
#           DrawableBase, and it does NOT carry LightAttributes.)
#   .ydd -> YddFile.Drawables[i].LightAttributes        (every drawable in the dictionary)
# The same split shows in the XML: <Fragment><Lights> exists,
# <Fragment><Drawable><Lights> does NOT.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_lights.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_lights.ps1 -Sample 400

param(
    [string] $GtaFolder,
    [string] $CodeWalker,
    [string] $Out,
    [Alias('Ornek')]
    [int]    $Sample = 0      # >0 = sampling mode (to measure speed)
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

    static void Row(StringBuilder sb, string model, string ext, int idx, LightAttributes L)
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

    static int WriteList(StringBuilder sb, string model, string ext,
                         ResourceSimpleList64<LightAttributes> list)
    {
        if (list == null) return 0;
        var it = list.data_items;
        if (it == null || it.Length == 0) return 0;
        for (int i = 0; i < it.Length; i++) Row(sb, model, ext, i, it[i]);
        return it.Length;
    }

    public static void Run(string gtaFolder, string outFolder, int sample)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        var targets = new List<RpfFileEntry>();
        foreach (var rpf in man.AllRpfs)
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null) continue;
                var n = fe.NameLower;
                if (n.EndsWith(".ydr") || n.EndsWith(".yft") || n.EndsWith(".ydd")) targets.Add(fe);
            }
        Console.WriteLine("[*] files to scan: {0}", targets.Count);

        int step = 1;
        if (sample > 0 && targets.Count > sample) step = targets.Count / sample;

        var sb = new StringBuilder(1 << 22);
        sb.Append("model\text\tidx\ttype\tcolour\tintensity\tfalloff\tfalloffExp\t");
        sb.Append("coneInner\tconeOuter\tcoronaSize\tcoronaIntensity\tvolumeIntensity\t");
        sb.Append("volumeSizeScale\tflags\ttimeFlags\tboneId\tgroupId\tflashiness\t");
        sb.Append("shadowBlur\tshadowNearClip\tprojTex\n");

        var t0 = DateTime.Now;
        int readCount = 0, errors = 0, filesWithLights = 0;
        long nLights = 0;
        string firstError = null;

        for (int i = 0; i < targets.Count; i += step)
        {
            var fe = targets[i];
            try
            {
                var data = fe.File.ExtractFile(fe);
                if (data == null || data.Length == 0) { errors++; continue; }
                var n = fe.NameLower;
                string model = fe.Name;
                int k = model.LastIndexOf('.');
                if (k > 0) model = model.Substring(0, k);
                int found = 0;

                if (n.EndsWith(".ydr"))
                {
                    var f = new YdrFile(); f.Load(data, fe); readCount++;
                    if (f.Drawable != null) found = WriteList(sb, model, "ydr", f.Drawable.LightAttributes);
                }
                else if (n.EndsWith(".yft"))
                {
                    var f = new YftFile(); f.Load(data, fe); readCount++;
                    // CAREFUL: Fragment.LightAttributes -- NOT Fragment.Drawable.
                    if (f.Fragment != null) found = WriteList(sb, model, "yft", f.Fragment.LightAttributes);
                }
                else
                {
                    var f = new YddFile(); f.Load(data, fe); readCount++;
                    if (f.Drawables != null)
                        for (int d = 0; d < f.Drawables.Length; d++)
                        {
                            var dr = f.Drawables[d];
                            if (dr == null) continue;
                            string name = (dr.Name == null) ? model : dr.Name;
                            found += WriteList(sb, name, "ydd", dr.LightAttributes);
                        }
                }

                if (found > 0) { filesWithLights++; nLights += found; }
            }
            catch (Exception ex)
            {
                errors++;
                if (firstError == null) firstError = fe.Name + ": " + ex.Message;
            }

            if (readCount > 0 && readCount % 20000 == 0)
                Console.WriteLine("    ... {0} files, {1} lights, {2:0} s",
                                  readCount, nLights, (DateTime.Now - t0).TotalSeconds);
        }

        Console.WriteLine("[*] read: {0}, errors: {1}", readCount, errors);
        if (firstError != null) Console.WriteLine("[!] first error: {0}", firstError);
        Console.WriteLine("[*] files with lights: {0} ({1:0.00}%)  total lights: {2}",
                          filesWithLights, 100.0 * filesWithLights / Math.Max(1, readCount), nLights);

        if (sample > 0)
        {
            double secs = (DateTime.Now - t0).TotalSeconds;
            Console.WriteLine("[*] SAMPLE: {0:0.0} s / {1} files -> estimated full scan {2:0.0} min",
                              secs, readCount, (secs / Math.Max(1, readCount)) * targets.Count / 60.0);
            return;   // sampling mode writes NO FILE (so partial data does not persist)
        }

        var outPath = Path.Combine(outFolder, "lights.tsv.gz");
        var raw = Encoding.UTF8.GetBytes(sb.ToString());
        using (var fs = File.Create(outPath))
        using (var gz = new GZipStream(fs, CompressionLevel.Optimal))
            gz.Write(raw, 0, raw.Length);

        Console.WriteLine("[+] lights.tsv.gz  ({0} lights / {1} files)", nLights, filesWithLights);
        Console.WriteLine("[+] {0:0.0} s", (DateTime.Now - t0).TotalSeconds);
    }
}
'@

$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'mscorlib', 'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console',
          'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[LightIndexer]::Run($GtaFolder, $Out, $Sample)
