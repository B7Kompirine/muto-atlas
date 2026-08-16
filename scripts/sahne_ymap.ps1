# sahne_ymap.ps1 - sahne editorunde yerlestirilen objelerden TEK bir .ymap uretir.
#
# NEDEN AYRI: make_prop_ymap.ps1 bir VANILLA prop'un mevcut yerlesimlerini
# taklit eder (kaynak model -> hedef model). Burada yerlesimler kullanicinin
# tarayicida elle koydugu yerlerdir ve hepsi TEK ymap'e girer.
#
# OLCULEN TUZAKLAR (make_prop_ymap.ps1'den devralindi, tekrar kesfedilmesin):
#   * CEntityDef'leri DOGRUDAN yazmak yetmez: Save() seri hale getirirken
#     AllEntities'ten uretir. Dogrudan yazinca dosya olusur, ICINDE 0 ENTITY olur.
#   * CalcFlags() CAGIRMA: contentFlags'i yeniden hesaplayip 65'i 1'e dusurur.
#   * CalcExtents() KULLANMA: archetype bu baglamda cozulmedigi icin entity
#     kutusunu SIFIR BOYUTLU birakir; sifir kutulu ymap streamlenmez.
#   * Extent entity'lerin BIRLESIMINDEN hesaplanir. Extent disinda kalan entity
#     sessizce hic gorunmez.
#
# Kullanim:
#   powershell -File sahne_ymap.ps1 -Json sahne.json -YmapName muto_sahne `
#              -OutFile "<...>\stream\muto_sahne.ymap"
#
# Json bicimi: { "objeler": [ {"arketip":"ad","konum":[x,y,z],
#                             "donus":[x,y,z,w],"yaricap":2.0,"lodDist":160} ] }

param(
    [Parameter(Mandatory=$true)][string] $Json,
    [Parameter(Mandatory=$true)][string] $YmapName,
    [Parameter(Mandatory=$true)][string] $OutFile,
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

$CodeWalker = & "$PSScriptRoot\yol.ps1" codewalker $CodeWalker
if (-not $CodeWalker) { throw "CodeWalker.Core.dll bulunamadi. python assetdb.py yol codewalker ""<yol>""" }

$cwDir = Split-Path $CodeWalker -Parent
$script:cwDir = $cwDir
[System.AppDomain]::CurrentDomain.add_AssemblyResolve([System.ResolveEventHandler]{
    param($sender, $e)
    $short = ($e.Name -split ',')[0]
    $p = Join-Path $script:cwDir "$short.dll"
    if (Test-Path -LiteralPath $p) { return [System.Reflection.Assembly]::LoadFrom($p) }
    return $null
})

if (-not (Test-Path -LiteralPath $Json)) { throw "sahne json yok: $Json" }
$sahne = Get-Content -LiteralPath $Json -Raw | ConvertFrom-Json
if (-not $sahne.objeler -or $sahne.objeler.Count -eq 0) { throw "sahnede obje yok" }

$src = @'
using System;
using System.Collections.Generic;
using System.IO;
using CodeWalker.GameFiles;
using SharpDX;

public static class SahneYmap
{
    public static uint Joaat(string s)
    {
        uint h = 0; s = s.ToLowerInvariant();
        foreach (char c in s) { h += c; h += h << 10; h ^= h >> 6; }
        h += h << 3; h ^= h >> 11; h += h << 15;
        return h;
    }

    public static string Yaz(string ymapName, string outPath,
                             string[] arketip, float[][] konum, float[][] donus,
                             float[] yaricap, float lodDist)
    {
        var outY = new YmapFile();
        outY.Name = ymapName;

        var yents = new List<YmapEntityDef>();
        var eMin = new Vector3(float.MaxValue, float.MaxValue, float.MaxValue);
        var eMax = new Vector3(float.MinValue, float.MinValue, float.MinValue);

        for (int i = 0; i < arketip.Length; i++)
        {
            var ed = new CEntityDef();
            ed.archetypeName = new MetaHash(Joaat(arketip[i]));
            ed.position = new Vector3(konum[i][0], konum[i][1], konum[i][2]);
            ed.rotation = new Vector4(donus[i][0], donus[i][1], donus[i][2], donus[i][3]);
            ed.scaleXY = 1.0f;
            ed.scaleZ = 1.0f;
            ed.parentIndex = -1;
            ed.lodDist = lodDist;
            ed.childLodDist = 0;
            ed.lodLevel = rage__eLodType.LODTYPES_DEPTH_ORPHANHD;
            ed.numChildren = 0;
            ed.priorityLevel = rage__ePriorityLevel.PRI_REQUIRED;
            ed.flags = 1572872;
            ed.ambientOcclusionMultiplier = 255;
            ed.artificialAmbientOcclusion = 255;

            var e2 = ed;
            yents.Add(new YmapEntityDef(outY, i, ref e2));

            // Extent BIRLESIMDEN: disarida kalan entity sessizce gorunmez.
            float r = yaricap[i] > 0f ? yaricap[i] : 2.0f;
            var p = ed.position;
            if (p.X - r < eMin.X) eMin.X = p.X - r;
            if (p.Y - r < eMin.Y) eMin.Y = p.Y - r;
            if (p.Z - r < eMin.Z) eMin.Z = p.Z - r;
            if (p.X + r > eMax.X) eMax.X = p.X + r;
            if (p.Y + r > eMax.Y) eMax.Y = p.Y + r;
            if (p.Z + r > eMax.Z) eMax.Z = p.Z + r;
        }

        outY.AllEntities  = yents.ToArray();
        outY.RootEntities = yents.ToArray();
        outY.BuildCEntityDefs();

        var cmd = outY.CMapData;
        cmd.name                = new MetaHash(Joaat(ymapName));
        cmd.parent              = new MetaHash(0);
        cmd.flags               = 0;
        cmd.contentFlags        = 65;
        cmd.entitiesExtentsMin  = eMin;
        cmd.entitiesExtentsMax  = eMax;
        cmd.streamingExtentsMin = new Vector3(eMin.X - lodDist, eMin.Y - lodDist, eMin.Z - lodDist);
        cmd.streamingExtentsMax = new Vector3(eMax.X + lodDist, eMax.Y + lodDist, eMax.Z + lodDist);
        outY.CMapData           = cmd;

        File.WriteAllBytes(outPath, outY.Save());

        // GERI OKU: tek gecerli olcut budur, dosya boyutu degil.
        var chk = RpfFile.GetResourceFile<YmapFile>(File.ReadAllBytes(outPath));
        int n = (chk != null && chk.CEntityDefs != null) ? chk.CEntityDefs.Length : 0;
        var cc = chk.CMapData;
        return string.Format("entity={0} extent=({1:0.##},{2:0.##},{3:0.##})-({4:0.##},{5:0.##},{6:0.##}) contentFlags={7}",
            n, cc.entitiesExtentsMin.X, cc.entitiesExtentsMin.Y, cc.entitiesExtentsMin.Z,
            cc.entitiesExtentsMax.X, cc.entitiesExtentsMax.Y, cc.entitiesExtentsMax.Z, cc.contentFlags);
    }
}
'@

$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'),
          'netstandard', 'System.Collections', 'System.Runtime', 'mscorlib')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

# ⛔ Betikler `powershell` (Windows PowerShell 5.1) ile cagriliyor, `pwsh` ile
#    degil. `[single](if (...) {...} else {...})` 5.1'de AYRISMAZ ve hata
#    "'if' is not recognized as a cmdlet" diye gelir -- sebebi gizler.
#    Ara degisken kullan.
$ark = @(); $kon = @(); $don = @(); $yar = @()
foreach ($o in $sahne.objeler) {
    $ark += [string]$o.arketip
    $kon += ,([single[]]@($o.konum[0], $o.konum[1], $o.konum[2]))
    $d = @(0,0,0,1)
    if ($o.donus) { $d = $o.donus }
    $don += ,([single[]]@($d[0], $d[1], $d[2], $d[3]))
    $r = 2.0
    if ($o.yaricap) { $r = $o.yaricap }
    $yar += [single]$r
}
$lod = 160.0
if ($sahne.lodDist) { $lod = $sahne.lodDist }
$lod = [single]$lod

$sonuc = [SahneYmap]::Yaz($YmapName, $OutFile, $ark, $kon, $don, $yar, $lod)
Write-Host "[+] $OutFile"
Write-Host "[=] geri okundu: $sonuc"
if ($sonuc -notmatch 'entity=(\d+)' -or [int]$Matches[1] -ne $ark.Count) {
    throw "DOGRULAMA BASARISIZ: $($ark.Count) entity yazildi, geri okumada farkli."
}
