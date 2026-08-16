# yol.ps1 - dis arac yollarini data/config.json'dan cozer (PowerShell tarafi).
#
# NEDEN: ayni yollar betiklere dagilmisti (CodeWalker icin 29, GTA icin 23
# ayri sabit tahmin). Kullanici araci baska yere kurunca hepsi elle
# duzeltiliyordu. Python tarafinin kutugu ile AYNI dosya okunur: yol.py.
#
# ⛔ PowerShell OLMAYAN property'de hata vermez, $null doner. Bu yuzden
#    anahtar adlari burada TEK YERDE tutulur; yanlis yazilan bir anahtar
#    "yapilandirma yok" gibi gorunup sessizce sabit tahmine duserdi --
#    ytd_ara.ps1'de tam olarak bu oldu (`gta` yazildi, dogrusu `gtaFolder`).
#
# IKI KULLANIM SEKLI VAR:
#
#   1) CAGIR (tek satir, en yaygin):
#        $CodeWalker = & "$PSScriptRoot\yol.ps1" codewalker $CodeWalker
#        $GtaFolder  = & "$PSScriptRoot\yol.ps1" gta        $GtaFolder
#      Bulunamazsa BOS doner; cagiran taraf kendi hatasini verir.
#
#   2) DOT-SOURCE (birden fazla yol lazimsa):
#        . (Join-Path $PSScriptRoot 'yol.ps1')
#        $CodeWalker = Coz-Yol codewalker $CodeWalker
#
# param() bir betigin ILK ifadesi olmak zorundadir; bu yuzden dot-source
# param'dan once YAPILAMAZ. 1. sekil bu yuzden var.

$script:MutoConfig = Join-Path (Split-Path $PSScriptRoot -Parent) 'data\config.json'

$script:MutoYollar = @{
  codewalker = @{
    anahtar = 'codeWalker'; tip = 'dosya'
    adaylar = @(
      "$env:USERPROFILE\Desktop\FiveM\CodeWalker30_dev46\CodeWalker.Core.dll",
      "$env:USERPROFILE\Desktop\CodeWalker\CodeWalker.Core.dll",
      "$env:USERPROFILE\Desktop\Programlar\CodeWalker\CodeWalker.Core.dll")
  }
  gta = @{
    anahtar = 'gtaFolder'; tip = 'klasor'
    adaylar = @(
      'C:\Program Files\Rockstar Games\Grand Theft Auto V',
      'C:\Program Files\Epic Games\GTAV',
      'C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V',
      'C:\SteamLibrary\steamapps\common\Grand Theft Auto V',
      'D:\SteamLibrary\steamapps\common\Grand Theft Auto V',
      'E:\Grand Theft Auto V')
  }
  sunucu  = @{ anahtar = 'resources'; tip = 'klasor'; adaylar = @() }
  blender = @{ anahtar = 'blender';   tip = 'dosya';  adaylar = @() }
}

function Get-MutoConfig {
    if (-not (Test-Path -LiteralPath $script:MutoConfig)) { return @{} }
    try { return (Get-Content -LiteralPath $script:MutoConfig -Raw | ConvertFrom-Json) }
    catch { return @{} }
}

function Test-MutoYol([string]$Yol, [string]$Tip) {
    if (-not $Yol) { return $false }
    # Kose parantezli yollarda -LiteralPath sart: yoksa joker sanilir.
    if ($Tip -eq 'klasor') { return (Test-Path -LiteralPath $Yol -PathType Container) }
    return (Test-Path -LiteralPath $Yol -PathType Leaf)
}

function Coz-Yol {
    <#
      Sira: acikca verilen (-Verilen) -> config.json -> bilinen adaylar.
      Bulunamazsa $null doner; cagiran taraf HATA VERMELI, sessizce gecmemeli.
    #>
    param(
        [Parameter(Mandatory=$true)][string]$Ad,
        [string]$Verilen
    )
    if ($Verilen) { return $Verilen }
    $k = $script:MutoYollar[$Ad.ToLower()]
    if (-not $k) { $k = @{ anahtar = "yol_$($Ad.ToLower())"; tip = 'dosya'; adaylar = @() } }

    $cfg = Get-MutoConfig
    # Property VARLIGINI sor: olmayan property $null doner ve sebep kaybolur.
    $yazili = $null
    if ($cfg -and $cfg.PSObject.Properties[$k.anahtar]) {
        $yazili = $cfg.PSObject.Properties[$k.anahtar].Value
    }
    if ($yazili) {
        if (Test-MutoYol $yazili $k.tip) { return $yazili }
        Write-Host "[!] config.json'da '$($k.anahtar)' yazili ama diskte YOK: $yazili"
    }
    foreach ($a in $k.adaylar) { if (Test-MutoYol $a $k.tip) { return $a } }
    return $null
}

function Coz-YolZorunlu {
    param([Parameter(Mandatory=$true)][string]$Ad, [string]$Verilen)
    $p = Coz-Yol -Ad $Ad -Verilen $Verilen
    if (-not $p) {
        throw ("'$Ad' yolu bulunamadi. Ayarla:  python assetdb.py yol $Ad ""<yol>""")
    }
    return $p
}

# --- CAGRILDIGINDA: yolu yazdir. Dot-source edildiginde $args bos olur ve
#     bu blok calismaz, yani iki kullanim sekli catismaz.
if ($args.Count -ge 1) {
    Coz-Yol -Ad $args[0] -Verilen $(if ($args.Count -ge 2) { $args[1] } else { $null })
}
