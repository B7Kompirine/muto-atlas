# cw_anim_check.ps1 — derlenmis bir .ycd'yi OYUNA GIRMEDEN degerlendirir.
#
# NEDEN: bir animasyonu test etmek icin sunucuya baglanmak pahali — FiveM
# stream dosyalarini cache'ledigi icin her denemede tam cikis/giris gerekiyor.
# CodeWalker'in Model Viewer'i klipleri oynatabiliyor (ClipDictComboBox +
# SelectClip) ama GUI. Burada AYNI CodeWalker.Core kodu headless kullaniliyor:
# klip hangi kemige, hangi karede, hangi degeri yaziyor - sayiyla.
#
# Kullanim (dizi parametreleri -Command ile gecilmeli, -File ile TEK STRING olur):
#   powershell -Command "& cw_anim_check.ps1 -Ycd <x.ycd> -Clip level -Tags @(63316)"
#
# Track: 0 = oteleme, 1 = donus
#
# UC TUZAK (uculu de yasandi, kod bunlara gore yazildi):
#   - Add-Type'a 'netstandard' referansi verilmezse generic cagri derlenmez.
#   - ClipBase.Name OKUNMAZ -> StackOverflow, surec exit 253 ile oluyor,
#     hata mesaji bile yok. Klip adi ClipMapEntry.Hash'te.
#   - Animation.BoneIds dizi degil, ResourceSimpleList64_s<> -> .data_items

param(
    [Parameter(Mandatory=$true)][string] $Ycd,
    [string]   $Clip,
    [int[]]    $Tags   = @(),
    [double[]] $Phases = @(0.0, 0.25, 0.5, 0.75, 1.0),
    [string]   $CodeWalker
)

$ErrorActionPreference = 'Stop'

if (-not $CodeWalker) {
    $CodeWalker = @(
        "$env:USERPROFILE\Desktop\FiveM\CodeWalker30_dev46\CodeWalker.Core.dll",
        "$env:USERPROFILE\Desktop\CodeWalker\CodeWalker.Core.dll"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $CodeWalker) { throw "CodeWalker.Core.dll bulunamadi." }
if (-not (Test-Path -LiteralPath $Ycd)) { throw "ycd bulunamadi: $Ycd" }

$cwDir = Split-Path $CodeWalker -Parent
$script:cwDir = $cwDir
[System.AppDomain]::CurrentDomain.add_AssemblyResolve([System.ResolveEventHandler]{
    param($sender, $e)
    $short = ($e.Name -split ',')[0]
    $p = Join-Path $script:cwDir "$short.dll"
    if (Test-Path -LiteralPath $p) { [System.Reflection.Assembly]::LoadFrom($p) } else { $null }
})
[void][System.Reflection.Assembly]::LoadFrom($CodeWalker)

$src = @'
using System;
using System.Collections.Generic;
using System.Text;
using CodeWalker.GameFiles;
using SharpDX;

public static class AnimCheck
{
    public static string Run(string path, string clipName, int[] tags, double[] phases)
    {
        var sb = new StringBuilder();
        byte[] data = System.IO.File.ReadAllBytes(path);
        var ycd = RpfFile.GetResourceFile<YcdFile>(data);
        ycd.Name = System.IO.Path.GetFileName(path);

        var cmes = ycd.ClipMapEntries;
        sb.AppendLine("dosya : " + ycd.Name);
        sb.AppendLine("klip  : " + (cmes == null ? 0 : cmes.Length));
        sb.AppendLine();
        if (cmes == null) return sb.ToString();

        foreach (var cme in cmes)
        {
            if (cme == null || cme.Clip == null) continue;
            string nm = cme.Hash.ToString();     // ClipBase.Name OKUMA (StackOverflow)
            if (!string.IsNullOrEmpty(clipName) &&
                nm.IndexOf(clipName, StringComparison.OrdinalIgnoreCase) < 0) continue;

            var ca = cme.Clip as ClipAnimation;
            if (ca == null || ca.Animation == null)
            {
                sb.AppendLine("klip '" + nm + "': tek animasyonlu degil (" + cme.Clip.GetType().Name + ")");
                continue;
            }
            var an = ca.Animation;
            sb.AppendLine("=== " + nm + " ===  kare=" + an.Frames +
                          "  sure=" + an.Duration.ToString("0.000") + "s" +
                          "  kanal=" + an.BoneIds.data_items.Length);

            var useTags = new List<int>();
            if (tags != null && tags.Length > 0) useTags.AddRange(tags);
            else
            {
                var seen = new HashSet<int>();
                foreach (var b in an.BoneIds.data_items)
                    if (seen.Add(b.BoneId)) useTags.Add(b.BoneId);
            }

            foreach (int tag in useTags)
            {
                int iT = an.FindBoneIndex((ushort)tag, 0);
                int iR = an.FindBoneIndex((ushort)tag, 1);
                if (iT < 0 && iR < 0) { sb.AppendLine("  tag " + tag + ": kanal yok"); continue; }
                sb.AppendLine("  tag " + tag + ":");
                foreach (double ph in phases)
                {
                    float t = (float)(ph * an.Duration);
                    var fp = an.GetFramePosition(t);
                    string line = "     faz " + ph.ToString("0.00");
                    if (iT >= 0)
                    {
                        Vector4 v = an.EvaluateVector4(fp, iT, true);
                        line += "  pos=(" + v.X.ToString("0.0000") + "," +
                                v.Y.ToString("0.0000") + "," + v.Z.ToString("0.0000") + ")";
                    }
                    if (iR >= 0)
                    {
                        Quaternion q = an.EvaluateQuaternion(fp, iR, true);
                        double w = Math.Abs((double)q.W); if (w > 1.0) w = 1.0;
                        line += "  aci=" + (2.0 * Math.Acos(w) * 180.0 / Math.PI).ToString("0.00") + "d";
                    }
                    sb.AppendLine(line);
                }
            }
            sb.AppendLine();
        }
        return sb.ToString();
    }
}
'@

$refs = @(
    $CodeWalker,
    (Join-Path $cwDir 'SharpDX.dll'),
    (Join-Path $cwDir 'SharpDX.Mathematics.dll'),
    'netstandard'
)
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[AnimCheck]::Run($Ycd, $Clip, $Tags, $Phases)
