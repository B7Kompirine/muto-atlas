# ptfx_make.ps1 - builds and deploys a custom particle effect WITH ONE COMMAND.
#
# The whole pipeline: texture -> XML -> binary .ypt -> verification -> stream/
# None of the intermediate steps has to be run by hand.
#
# EXAMPLES
#   # soft round sprite, green, drifting upwards
#   .\ptfx_make.ps1 -Name my_spore -Color 0.2,0.9,0.35 -Target <stream folder>
#
#   # from your own PNG (grey mask: black background, shape in alpha)
#   .\ptfx_make.ps1 -Name my_butterfly -Image butterfly.png -Color 0.15,0.6,1 `
#       -Size 0.4 -Lifetime 6 -Rate 4 -Rise 0.8 -Target <stream folder>
#
# !! LIMIT: a sprite sheet (frame-by-frame animation) does not work in an EMBEDDED texture.
#    Measured: the same texture is sliced when it is referenced from core.ypt, but not
#    when it is embedded in our file. The cause was not found. That is why this
#    script makes a SINGLE-FRAME texture -- a static sprite. Color, size,
#    lifetime, spawn rate, rise and your own image work without problems.

param(
    [Parameter(Mandatory = $true)][Alias('Ad')][string] $Name,
    [Alias('Gorsel')][string]     $Image,                   # ready PNG (grey mask)
    # The old values yumusak/halka/sert are still accepted; they are mapped below.
    [ValidateSet('soft', 'ring', 'hard', 'yumusak', 'halka', 'sert')][Alias('Desen')][string] $Pattern = 'soft',
    [Alias('DokuBoyut')][int]     $TextureSize = 128,
    [Alias('Renk')][double[]]     $Color    = @(0.2, 0.9, 0.35),  # color at birth
    [Alias('Renk2')][double[]]    $Color2,                        # color at death (transition)
    [Alias('Boyut')][double]      $Size     = 0.35,               # metres
    [Alias('Omur')][double]       $Lifetime = 3.0,                # seconds
    [Alias('Oran')][double]       $Rate     = 8.0,                # particles/second
    [Alias('Yaricap')][double]    $Radius   = 0.45,               # spawn sphere (m)
    [Alias('Yukselme')][double]   $Rise     = 0.4,                # target domain Z (m)
    [Alias('Alfa')][double]       $Alpha    = 1.0,
    # --- behaviours that bring the look to life (0 = off) ---
    [Alias('Ivme')][double]       $Accel    = 0.0,      # Z acceleration: rising smoke speeds up
    [Alias('Donme')][double]      $Spin     = 0.0,      # degrees/s: brings a static blob to life
    [Alias('Gurultu')][double]    $Noise    = 0.0,      # turbulence: smoke curls
    [Alias('Sekme')][double]      $Bounce   = 0.0,      # Collision: 0 sticks, 1 full bounce
    [Alias('Isik')][double]       $Light    = 0.0,      # the particle emits REAL light
    [Alias('IsikMenzil')][double] $LightRange = 3.0,
    [Alias('Parlama')][double]    $Emissive = 0.0,      # emissive: self-lit
    [Alias('Hedef')][string]      $Target,                          # stream/ folder
    [Alias('Calisma')][string]    $WorkDir                          # intermediate files
)

$ErrorActionPreference = 'Stop'
# Old pattern names -> the names make_dds.py uses.
$patternMap = @{ yumusak = 'soft'; halka = 'ring'; sert = 'hard' }
if ($patternMap.ContainsKey($Pattern)) { $Pattern = $patternMap[$Pattern] }

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $WorkDir) { $WorkDir = Join-Path $env:TEMP "ptfx_$Name" }
# In New-Item, -LiteralPath does not work together with -Force; use -Path.
if (-not (Test-Path -LiteralPath $WorkDir)) {
    New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
}

$texture = $Name     # texture name = effect name (avoids confusion)
$dds  = Join-Path $WorkDir "$texture.dds"

Write-Host "=== 1/3  texture ===" -ForegroundColor Cyan
if ($Image) {
    if (-not (Test-Path -LiteralPath $Image)) { throw "image not found: $Image" }
    python "$scriptDir\make_dds.py" $dds --source $Image
} else {
    python "$scriptDir\make_dds.py" $dds --pattern $Pattern --size $TextureSize
}
if ($LASTEXITCODE -ne 0) { throw "texture could not be built" }

Write-Host "=== 2/3  XML ===" -ForegroundColor Cyan
$pyArgs = @('--name', $Name, '--texture', $texture, '--folder', $WorkDir,
            '--color', $Color[0], $Color[1], $Color[2],
            '--lifetime', $Lifetime, '--size', $Size, '--rate', $Rate,
            '--radius', $Radius, '--rise', $Rise, '--alpha', $Alpha)
if ($Color2) { $pyArgs += @('--color2', $Color2[0], $Color2[1], $Color2[2]) }
foreach ($p in @(@('--accel', $Accel), @('--spin', $Spin), @('--noise', $Noise),
                 @('--bounce', $Bounce), @('--light', $Light), @('--emissive', $Emissive))) {
    if ($p[1] -ne 0) { $pyArgs += @($p[0], $p[1]) }
}
if ($Light -ne 0) { $pyArgs += @('--light-range', $LightRange) }
python "$scriptDir\build_custom_ptfx.py" @pyArgs
if ($LASTEXITCODE -ne 0) { throw "XML could not be built" }

Write-Host "=== 3/3  binary + verification ===" -ForegroundColor Cyan
# This step fills in the fields CodeWalker does not write (FxcFileHash, VFT,
# FileVFT, ShaderVar VFT) and FAILS if any of them stays zero.
$argv = @('-NoProfile', '-File', "$scriptDir\ypt_xml_to_bin.ps1",
          '-Xml', (Join-Path $WorkDir "$Name.ypt.xml"))
if ($Target) { $argv += @('-Deploy', $Target) }
& powershell @argv
if ($LASTEXITCODE -ne 0) { throw "binary build/verification failed" }

Write-Host ""
Write-Host "[=] READY: $Name" -ForegroundColor Green
Write-Host "    Lua side:"
Write-Host "      RequestNamedPtfxAsset('$Name')          -- ASSET = file name"
Write-Host "      UseParticleFxAssetNextCall('$Name')     -- before EVERY call"
Write-Host "      StartParticleFxLoopedAtCoord('$Name', x,y,z, 0,0,0, 1.0, ...)"
Write-Host ""
Write-Host "    ! stream/ changed: leave the server and reconnect." -ForegroundColor Yellow
