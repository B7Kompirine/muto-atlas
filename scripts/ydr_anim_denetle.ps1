# ydr_anim_denetle.ps1 — animasyonlu (skinned) .ydr icin Bag C + Bag D denetimi.
#
# NEDEN: Sollumz iki alani sessizce bos/yanlis birakir ve ikisi de oyunda
# "animasyon oynamiyor" olarak gorunur, hicbir arac uyarmaz:
#
#   Bag D  kemik Flags = 0        -> kemik hicbir donusum kabul etmez.
#          Klip bulunur, PlayEntityAnim 1 doner, animTime 0->1 ilerler,
#          faz sayar, MESH REST POZUNDA KALIR. Konsolda hata yoktur.
#          Vanilla/crane olcumu: kok 4215 (=119|Unk0), digerleri 119
#          (RotX|RotY|RotZ|TransX|TransY|TransZ).
#
#   Bag C  Drawable BoundingBox   -> Sollumz REST kutusunu yazar. Animasyon
#          kutunun disina cikarsa obje uzakta titrer ve kaybolur.
#          NOT: ytyp arketip kutusu AYRI bir alandir, o da duzeltilmeli.
#
# Kullanim:
#   powershell -File ydr_anim_denetle.ps1 -Ydr x.ydr
#   powershell -File ydr_anim_denetle.ps1 -Ydr x.ydr -Duzelt
#   powershell -File ydr_anim_denetle.ps1 -Ydr x.ydr -Duzelt `
#              -BbMin '-53.98,-29.37,-0.6' -BbMax '29.65,40.3,30.98'
#
# -Duzelt verilmezse SADECE rapor eder, dosyaya dokunmaz.
# Duzeltirken once .yedek alir, sonra GERI OKUYUP dogrular.

param(
    [Parameter(Mandatory=$true)][string] $Ydr,
    [switch] $Duzelt,
    [string] $BbMin,
    [string] $BbMax,
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

# Yol icinde [harita] gibi kose parantez varsa Test-Path onu joker sanar.
if (-not (Test-Path -LiteralPath $Ydr)) { throw "bulunamadi: $Ydr" }

if (-not $CodeWalker) {
    $CodeWalker = @(
        "$env:USERPROFILE\Desktop\FiveM\CodeWalker30_dev46\CodeWalker.Core.dll",
        "$env:USERPROFILE\Desktop\CodeWalker\CodeWalker.Core.dll"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $CodeWalker) { throw "CodeWalker.Core.dll bulunamadi." }
Add-Type -Path $CodeWalker

$KOK_FLAGS   = 4215     # 119 | Unk0(4096)
$DIGER_FLAGS = 119      # RotX|RotY|RotZ|TransX|TransY|TransZ

function Yukle([string]$p) {
    $d = [System.IO.File]::ReadAllBytes($p)
    $e = [CodeWalker.GameFiles.RpfFile]::CreateResourceFileEntry([ref]$d, 0)
    $d = [CodeWalker.GameFiles.ResourceBuilder]::Decompress($d)
    $y = New-Object CodeWalker.GameFiles.YdrFile
    $y.Load($d, $e)
    return $y
}

function V3([type]$T, $x, $y, $z) {
    return [System.Activator]::CreateInstance($T, @([single]$x, [single]$y, [single]$z))
}

$y  = Yukle $Ydr
$dr = $y.Drawable
$ad = [System.IO.Path]::GetFileName($Ydr)

if (-not $dr.Skeleton) {
    Write-Host "[=] $ad  iskelet YOK -- animasyonlu degil, denetim gerekmiyor."
    exit 0
}

$bn = $dr.Skeleton.Bones.Items
$sifir = @($bn | Where-Object { [int]$_.Flags -eq 0 }).Count
$kokF  = [int]$bn[0].Flags

Write-Host ("=== {0}" -f $ad)
Write-Host ("    kemik = {0}   kok Flags = {1}   sifir bayrakli = {2}" -f $bn.Count, $kokF, $sifir)
Write-Host ("    bbMin = ({0:N2},{1:N2},{2:N2})  bbMax = ({3:N2},{4:N2},{5:N2})  r = {6:N2}" -f `
    $dr.BoundingBoxMin.X, $dr.BoundingBoxMin.Y, $dr.BoundingBoxMin.Z,
    $dr.BoundingBoxMax.X, $dr.BoundingBoxMax.Y, $dr.BoundingBoxMax.Z, $dr.BoundingSphereRadius)

$bulgu = @()
if ($sifir -gt 0)            { $bulgu += "BAG D: $sifir kemikte Flags=0 -- animasyon SESSIZCE oynamaz" }
if ($kokF -ne $KOK_FLAGS)    { $bulgu += "BAG D: kok Flags=$kokF, olmasi gereken $KOK_FLAGS" }
if ($BbMin -and -not $BbMax) { throw "-BbMin verildi ama -BbMax yok" }

if ($bulgu.Count -eq 0 -and -not $BbMin) {
    Write-Host "[+] bulgu yok."
    exit 0
}
foreach ($b in $bulgu) { Write-Host "[!] $b" }
if ($BbMin) { Write-Host "[*] bbox elle verildi -> yazilacak" }

if (-not $Duzelt) {
    Write-Host "[i] -Duzelt verilmedi, dosyaya dokunulmadi."
    exit 1
}

# --- DUZELT
$yedek = "$Ydr.yedek"
if (-not (Test-Path -LiteralPath $yedek)) { Copy-Item -LiteralPath $Ydr -Destination $yedek -Force }

$T = [CodeWalker.GameFiles.EBoneFlags]
for ($i = 0; $i -lt $bn.Count; $i++) {
    $v = if ($i -eq 0) { $KOK_FLAGS } else { $DIGER_FLAGS }
    $bn[$i].Flags = [Enum]::ToObject($T, $v)
}
if ($BbMin) {
    $VT = $dr.BoundingBoxMin.GetType()
    $mn = $BbMin -split ','; $mx = $BbMax -split ','
    $dr.BoundingBoxMin = V3 $VT $mn[0] $mn[1] $mn[2]
    $dr.BoundingBoxMax = V3 $VT $mx[0] $mx[1] $mx[2]
    $c = @(0,1,2) | ForEach-Object { ([single]$mn[$_] + [single]$mx[$_]) / 2 }
    $dr.BoundingCenter = V3 $VT $c[0] $c[1] $c[2]
    $r = [Math]::Sqrt( (0,1,2 | ForEach-Object { [Math]::Pow((([single]$mx[$_] - [single]$mn[$_]) / 2), 2) } | Measure-Object -Sum).Sum )
    $dr.BoundingSphereRadius = [single]$r
}

# Sayimlari yazmadan ONCE al ki geri okumayla karsilastirabilelim.
$onceKemik = $bn.Count
$onceGeom  = $dr.AllModels[0].Geometries.Count
$onceVert  = $dr.AllModels[0].Geometries[0].VertexData.VertexCount

[System.IO.File]::WriteAllBytes($Ydr, $y.Save())

# --- GERI OKU. Boyut gecerlilik olcutu DEGILDIR (RSC7 zlib); tek olcut budur.
$g  = Yukle $Ydr
$gd = $g.Drawable
$gb = $gd.Skeleton.Bones.Items
$gs = @($gb | Where-Object { [int]$_.Flags -eq 0 }).Count
$ok = ($gs -eq 0) -and ([int]$gb[0].Flags -eq $KOK_FLAGS) -and
      ($gb.Count -eq $onceKemik) -and
      ($gd.AllModels[0].Geometries.Count -eq $onceGeom) -and
      ($gd.AllModels[0].Geometries[0].VertexData.VertexCount -eq $onceVert)

Write-Host ("[+] yazildi. geri okuma: kemik={0} geom={1} vert={2} sifirBayrak={3} kokFlags={4}" -f `
    $gb.Count, $gd.AllModels[0].Geometries.Count,
    $gd.AllModels[0].Geometries[0].VertexData.VertexCount, $gs, [int]$gb[0].Flags)

if (-not $ok) {
    Write-Host "[!] DOGRULAMA BASARISIZ -- yedekten geri aliniyor."
    Copy-Item -LiteralPath $yedek -Destination $Ydr -Force
    exit 1
}
Write-Host "[+] dogrulama tamam."
exit 0
