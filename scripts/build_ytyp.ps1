# build_ytyp.ps1 -- builds a binary .ytyp from a .ytyp.xml file.
#
# WHY: xml_to_res.ps1 does NOT SUPPORT the .ytyp extension ("unsupported extension")
#      and CodeWalker.Core has NO type called XmlYtyp. A ytyp is a meta/PSO
#      file; the right path is the general XmlMeta importer:
#        XmlMeta.GetXMLFormat(<file name>, [ref]$trim)  -> MetaFormat
#        XmlMeta.GetData($doc, $fmt, <output folder>)   -> byte[]
#
# !! Output size is NOT a validity measure -- RSC7 is zlib compressed.
#    That is why the script READS the file BACK after building it (YtypFile.Load) and
#    prints the archetype count / name / textureDictionary / assetType values.
#    If no archetype comes out, exit 1.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_ytyp.ps1 `
#       -XmlPath x.ytyp.xml -OutPath stream\x.ytyp [-CodeWalker <...dll>]

[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $XmlPath,
    [Parameter(Mandatory)][string] $OutPath,
    # No default: the path comes from data/config.json or from -CodeWalker.
    # Making a personal path the default fails silently on someone else's machine.
    [string] $CodeWalker = $(if ($env:MUTO_ATLAS_CODEWALKER) { $env:MUTO_ATLAS_CODEWALKER } else { '' })
)

$ErrorActionPreference = 'Stop'

if (-not $CodeWalker) {
    $cfg = Join-Path (Split-Path $PSScriptRoot -Parent) 'data\config.json'
    if (Test-Path -LiteralPath $cfg) {
        $CodeWalker = (Get-Content -LiteralPath $cfg -Raw | ConvertFrom-Json).codeWalker
    }
}
if (-not (Test-Path -LiteralPath $CodeWalker)) { throw "CodeWalker.Core.dll missing: $CodeWalker" }
if (-not (Test-Path -LiteralPath $XmlPath))    { throw "XML missing: $XmlPath" }

[void][System.Reflection.Assembly]::LoadFrom($CodeWalker)

# The XML is PARSED first: handing broken XML to CodeWalker gives a meaningless error.
$doc = New-Object System.Xml.XmlDocument
$doc.Load($XmlPath)

# Format detection is done from the file NAME (".ytyp.xml" -> RSC), not the path.
$name = [IO.Path]::GetFileName($XmlPath)
$trim = 0
$fmt = [CodeWalker.GameFiles.XmlMeta]::GetXMLFormat($name, [ref]$trim)
Write-Host "[i] format: $fmt (trim=$trim)"

$outDir = Split-Path -Parent $OutPath
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$data = [CodeWalker.GameFiles.XmlMeta]::GetData($doc, $fmt, $outDir)
if ($null -eq $data -or $data.Length -eq 0) { throw "GetData returned empty -- the XML schema may not be a ytyp" }
[IO.File]::WriteAllBytes($OutPath, $data)
Write-Host "[written] $OutPath  ($($data.Length) bytes, zlib compressed)"

# --- READ BACK: the only valid measure ---
Write-Host ''
Write-Host '=== READ BACK ==='
$bytes = [IO.File]::ReadAllBytes($OutPath)
$ytyp = New-Object CodeWalker.GameFiles.YtypFile
$ytyp.Load($bytes)      # single-argument overload: needs no RpfFileEntry
$archs = $ytyp.AllArchetypes
if ($null -eq $archs -or $archs.Count -lt 1) {
    Write-Host 'CHECK FAILED: no archetype could be read'
    exit 1
}
Write-Host "  archetype count: $($archs.Count)"
foreach ($a in $archs) {
    $bd = $a._BaseArchetypeDef
    Write-Host ("  name={0}  assetName={1}  textureDict={2}  assetType={3}" -f `
        $a.Name, $bd.assetName, $bd.textureDictionary, $bd.assetType)
    Write-Host ("     lodDist={0}  flags={1}  bbMin=({2})  bbMax=({3})" -f `
        $bd.lodDist, $bd.flags, $bd.bbMin, $bd.bbMax)
}
Write-Host 'ALL CHECKS PASSED'
