# ptfx_yap.ps1 — TEK KOMUTLA ozel partikul efekti uretir ve dagitir.
#
# Hattin tamami: doku -> XML -> ikili .ypt -> dogrulama -> stream/
# Ara adimlarin hicbirini elle calistirmaya gerek yok.
#
# ORNEKLER
#   # yumusak yuvarlak sprite, yesil, yukari suzulen
#   .\ptfx_yap.ps1 -Ad muto_spor -Renk 0.2,0.9,0.35 -Hedef <stream klasoru>
#
#   # kendi PNG'inden (gri maske: siyah zemin, sekil alfada)
#   .\ptfx_yap.ps1 -Ad muto_kelebek -Gorsel kelebek.png -Renk 0.15,0.6,1 `
#       -Boyut 0.4 -Omur 6 -Oran 4 -Yukselme 0.8 -Hedef <stream klasoru>
#
# ⛔ SINIR: sprite sheet (kare kare animasyon) GOMULU dokuda calismiyor.
#    Olculdu: ayni doku core.ypt'ten referansla dilimleniyor, bizim
#    dosyaya gomulunce dilimlenmiyor. Sebebi bulunamadi. Bu yuzden bu
#    betik TEK KARELIK doku uretir -- hareketsiz sprite. Renk, boyut,
#    omur, dogum orani, yukselme ve kendi gorselin sorunsuz calisiyor.

param(
    [Parameter(Mandatory = $true)][string]   $Ad,
    [string]   $Gorsel,                                   # hazir PNG (gri maske)
    [ValidateSet('yumusak', 'halka', 'sert')][string] $Desen = 'yumusak',
    [int]      $DokuBoyut = 128,
    [double[]] $Renk    = @(0.2, 0.9, 0.35),                # dogumdaki renk
    [double[]] $Renk2,                                      # olumdeki renk (gecis)
    [double]   $Boyut   = 0.35,                           # metre
    [double]   $Omur    = 3.0,                            # saniye
    [double]   $Oran    = 8.0,                            # parcacik/saniye
    [double]   $Yaricap = 0.45,                           # dogum kuresi (m)
    [double]   $Yukselme = 0.4,                           # target domain Z (m)
    [double]   $Alfa    = 1.0,
    # --- gorunumu canlandiran davranislar (0 = kapali) ---
    [double]   $Ivme    = 0.0,      # Z ivmesi: yukselen duman hizlanir
    [double]   $Donme   = 0.0,      # derece/sn: statik lekeyi canlandirir
    [double]   $Gurultu = 0.0,      # turbulans: duman kivrilir
    [double]   $Sekme   = 0.0,      # Collision: 0 yapisir, 1 tam seker
    [double]   $Isik    = 0.0,      # parcacik GERCEK isik yayar
    [double]   $IsikMenzil = 3.0,
    [double]   $Parlama = 0.0,      # emissive: kendinden isikli
    [string]   $Hedef,                                    # stream/ klasoru
    [string]   $Calisma                                   # ara dosyalar
)

$ErrorActionPreference = 'Stop'
$betik = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Calisma) { $Calisma = Join-Path $env:TEMP "ptfx_$Ad" }
# New-Item'da -LiteralPath ile -Force birlikte calismaz; -Path kullan.
if (-not (Test-Path -LiteralPath $Calisma)) {
    New-Item -ItemType Directory -Force -Path $Calisma | Out-Null
}

$doku = $Ad          # doku adi = efekt adi (karisikligi onler)
$dds  = Join-Path $Calisma "$doku.dds"

Write-Host "=== 1/3  doku ===" -ForegroundColor Cyan
if ($Gorsel) {
    if (-not (Test-Path -LiteralPath $Gorsel)) { throw "gorsel yok: $Gorsel" }
    python "$betik\make_dds.py" $dds --kaynak $Gorsel
} else {
    python "$betik\make_dds.py" $dds --desen $Desen --boyut $DokuBoyut
}
if ($LASTEXITCODE -ne 0) { throw "doku uretilemedi" }

Write-Host "=== 2/3  XML ===" -ForegroundColor Cyan
$py = @('--ad', $Ad, '--doku', $doku, '--klasor', $Calisma,
        '--renk', $Renk[0], $Renk[1], $Renk[2],
        '--omur', $Omur, '--boyut', $Boyut, '--oran', $Oran,
        '--yaricap', $Yaricap, '--yukselme', $Yukselme, '--alfa', $Alfa)
if ($Renk2) { $py += @('--renk2', $Renk2[0], $Renk2[1], $Renk2[2]) }
foreach ($p in @(@('--ivme', $Ivme), @('--donme', $Donme), @('--gurultu', $Gurultu),
                 @('--sekme', $Sekme), @('--isik', $Isik), @('--parlama', $Parlama))) {
    if ($p[1] -ne 0) { $py += @($p[0], $p[1]) }
}
if ($Isik -ne 0) { $py += @('--isik-menzil', $IsikMenzil) }
python "$betik\build_custom_ptfx.py" @py
if ($LASTEXITCODE -ne 0) { throw "XML uretilemedi" }

Write-Host "=== 3/3  ikili + dogrulama ===" -ForegroundColor Cyan
# Bu adim CodeWalker'in yazmadigi alanlari tamamlar (FxcFileHash, VFT,
# FileVFT, ShaderVar VFT) ve sifir kalirsa HATA verir.
$argv = @('-NoProfile', '-File', "$betik\ypt_xml_to_bin.ps1",
          '-Xml', (Join-Path $Calisma "$Ad.ypt.xml"))
if ($Hedef) { $argv += @('-Deploy', $Hedef) }
& powershell @argv
if ($LASTEXITCODE -ne 0) { throw "ikili uretim/dogrulama basarisiz" }

Write-Host ""
Write-Host "[=] HAZIR: $Ad" -ForegroundColor Green
Write-Host "    Lua tarafi:"
Write-Host "      RequestNamedPtfxAsset('$Ad')          -- VARLIK = dosya adi"
Write-Host "      UseParticleFxAssetNextCall('$Ad')     -- HER cagridan once"
Write-Host "      StartParticleFxLoopedAtCoord('$Ad', x,y,z, 0,0,0, 1.0, ...)"
Write-Host ""
Write-Host "    ⚠ stream/ degistigi icin sunucudan CIKIP yeniden baglan." -ForegroundColor Yellow
