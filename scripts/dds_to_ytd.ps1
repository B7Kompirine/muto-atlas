# dds_to_ytd.ps1 -- builds a .ytd texture dictionary from the .dds files in a folder.
#
# WHY: Blender CANNOT WRITE DDS (the 128-byte header is written by hand and Blender
#      stores pixels bottom-up) -- that gap is closed by bake_to_gta.py / make_dds.py;
#      this script then builds the .ytd once you have the .dds files.
#
#      VERSION NOTE (measured 2026-08-23): "Sollumz cannot build a .ytd" is NO LONGER
#      TRUE IN GENERAL. Sollumz 2.9.0 HAS bpy.ops.sollumz.export_ytd.
#      This script is still needed: it builds a .ytd from .dds folders made
#      outside Blender and verifies it by READING IT BACK after building --
#      the Sollumz export does no such check.
#
# !! Output size is NOT a validity measure -- RSC7 is zlib compressed.
#    That is why the script READS the file BACK after building it and verifies
#    texture count/name/format. If verification fails, exit 1.
#
# Usage:
#   pwsh dds_to_ytd.ps1 -Source out\ -OutPath stream\mtk_sidewalk.ytd
#   pwsh dds_to_ytd.ps1 -Source out\ -OutPath x.ytd -CodeWalker C:\...\CodeWalker.Core.dll

[CmdletBinding()]
param(
    [Parameter(Mandatory)][Alias('Girdi')][string] $Source,
    [Parameter(Mandatory)][Alias('Cikti')][string] $OutPath,
    # Do not put a texture the shader does NOT USE into the dictionary. Example: cutout_fence_normal
    # has no SpecSampler; '*_s.dds' would be ~175 KB of stream load for nothing.
    [Alias('Haric')][string[]] $Exclude = @(),
    # No default: the path comes from data/config.json or from -CodeWalker.
    # Making a personal path the default fails silently on someone else's machine.
    [string] $CodeWalker = $(if ($env:MUTO_ATLAS_CODEWALKER) { $env:MUTO_ATLAS_CODEWALKER } else { '' })
)

$ErrorActionPreference = 'Stop'

# If no path was given, read it from data/config.json (same behaviour as build_ytyp.ps1).
if (-not $CodeWalker) {
    $cfg = Join-Path (Split-Path $PSScriptRoot -Parent) 'data\config.json'
    if (Test-Path -LiteralPath $cfg) {
        $CodeWalker = (Get-Content -LiteralPath $cfg -Raw | ConvertFrom-Json).codeWalker
    }
}
if (-not (Test-Path -LiteralPath $CodeWalker)) { throw "CodeWalker.Core.dll missing: $CodeWalker" }
if (-not (Test-Path -LiteralPath $Source))     { throw "source folder missing: $Source" }
Add-Type -Path $CodeWalker

$allDds = @(Get-ChildItem -LiteralPath $Source -Filter *.dds -File | Sort-Object Name)
$ddsFiles = @($allDds | Where-Object { $fileName = $_.Name; -not ($Exclude | Where-Object { $fileName -like $_ }) })
foreach ($skipped in ($allDds | Where-Object { $ddsFiles -notcontains $_ })) {
    "  - {0,-28} EXCLUDED" -f $skipped.Name
}
if ($ddsFiles.Count -eq 0) { throw "no .dds in $Source (after filtering)" }

$textures = New-Object "System.Collections.Generic.List[CodeWalker.GameFiles.Texture]"
foreach ($f in $ddsFiles) {
    $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
    $tex   = [CodeWalker.Utils.DDSIO]::GetTexture($bytes)
    if (-not $tex) { throw "could not read DDS: $($f.Name)" }
    $tex.Name = $f.BaseName
    # !! The name hash is the key the engine finds the texture by; writing the name by hand
    #    and leaving the hash empty makes the texture impossible to find.
    $tex.NameHash = [CodeWalker.GameFiles.JenkHash]::GenHash($f.BaseName.ToLower())
    $textures.Add($tex)
    "  + {0,-28} {1}x{2} {3} mip={4}" -f $tex.Name, $tex.Width, $tex.Height, $tex.Format, $tex.Levels
}

$td = New-Object CodeWalker.GameFiles.TextureDictionary
$td.BuildFromTextureList($textures)
$ytd = New-Object CodeWalker.GameFiles.YtdFile
$ytd.TextureDict = $td
$data = $ytd.Save()

$outDir = Split-Path -Parent $OutPath
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
}
[System.IO.File]::WriteAllBytes($OutPath, $data)
"`n[written] $OutPath  ($('{0:N0}' -f $data.Length) bytes, zlib compressed)"

# ---- READ BACK: the only valid measure ------------------------------------
$raw      = [System.IO.File]::ReadAllBytes($OutPath)
$entry    = [CodeWalker.GameFiles.RpfFile]::CreateResourceFileEntry([ref]$raw, 0)
$unpacked = [CodeWalker.GameFiles.ResourceBuilder]::Decompress($raw)
$readBack = New-Object CodeWalker.GameFiles.YtdFile
$readBack.Load($unpacked, $entry)

$readTextures = @($readBack.TextureDict.Textures.data_items | Where-Object { $_ })
"`n=== READ BACK ==="
"  texture count: $($readTextures.Count) (expected $($textures.Count))"
$failCount = 0
if ($readTextures.Count -ne $textures.Count) { $failCount++ }
foreach ($t in $readTextures) {
    $expected = $textures | Where-Object { $_.Name -eq $t.Name } | Select-Object -First 1
    if (-not $expected) { "  ERROR: unexpected texture '$($t.Name)'"; $failCount++; continue }
    $ok = ($t.Width -eq $expected.Width) -and ($t.Height -eq $expected.Height) -and
          ($t.Format -eq $expected.Format) -and ($t.Levels -eq $expected.Levels)
    if (-not $ok) { $failCount++ }
    "  {0,-28} {1}x{2} {3} mip={4}  {5}" -f $t.Name, $t.Width, $t.Height, $t.Format,
        $t.Levels, $(if ($ok) { 'OK' } else { 'ERROR' })
    if ($t.NameHash -eq 0) { "    ERROR: NameHash 0 -- the engine cannot find this texture"; $failCount++ }
}

if ($failCount -gt 0) { "`n$failCount VERIFICATION ERROR(S)"; exit 1 }
"`nALL CHECKS PASSED"
exit 0
