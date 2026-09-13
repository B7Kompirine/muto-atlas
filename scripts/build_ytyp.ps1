# build_ytyp.ps1 -- .ytyp.xml dosyasindan binary .ytyp uretir.
#
# NEDEN: xml_to_res.ps1 .ytyp uzantisini DESTEKLEMIYOR ("desteklenmeyen uzanti")
#        ve CodeWalker.Core'da XmlYtyp diye bir tip YOKTUR. Ytyp bir meta/PSO
#        dosyasidir; dogru yol genel XmlMeta ice aktaricisidir:
#          XmlMeta.GetXMLFormat(<dosya adi>, [ref]$trim)  -> MetaFormat
#          XmlMeta.GetData($doc, $fmt, <cikti klasoru>)   -> byte[]
#
# !! Cikis boyutu gecerlilik olcutu DEGILDIR -- RSC7 zlib sikistirilmistir.
#    Bu yuzden betik uretimden sonra dosyayi GERI OKUR (YtypFile.Load) ve
#    archetype sayisi / ad / textureDictionary / assetType degerlerini basar.
#    Archetype cikmazsa exit 1.
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_ytyp.ps1 `
#       -XmlPath x.ytyp.xml -OutPath stream\x.ytyp [-CodeWalker <...dll>]

[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $XmlPath,
    [Parameter(Mandatory)][string] $OutPath,
    # Varsayilan yok: yol data/config.json'dan ya da -CodeWalker ile verilir.
    # Kisisel bir yolu varsayilan yapmak baskasinin makinesinde sessizce basarisiz olur.
    [string] $CodeWalker = $(if ($env:MUTO_ATLAS_CODEWALKER) { $env:MUTO_ATLAS_CODEWALKER } else { '' })
)

$ErrorActionPreference = 'Stop'

if (-not $CodeWalker) {
    $cfg = Join-Path (Split-Path $PSScriptRoot -Parent) 'data\config.json'
    if (Test-Path -LiteralPath $cfg) {
        $CodeWalker = (Get-Content -LiteralPath $cfg -Raw | ConvertFrom-Json).codeWalker
    }
}
if (-not (Test-Path -LiteralPath $CodeWalker)) { throw "CodeWalker.Core.dll yok: $CodeWalker" }
if (-not (Test-Path -LiteralPath $XmlPath))    { throw "XML yok: $XmlPath" }

[void][System.Reflection.Assembly]::LoadFrom($CodeWalker)

# XML once AYRISTIRILIR: bozuk XML'i CodeWalker'a vermek anlamsiz hata verir.
$doc = New-Object System.Xml.XmlDocument
$doc.Load($XmlPath)

# Format tespiti dosya ADINDAN yapilir (".ytyp.xml" -> RSC), yol degil.
$name = [IO.Path]::GetFileName($XmlPath)
$trim = 0
$fmt = [CodeWalker.GameFiles.XmlMeta]::GetXMLFormat($name, [ref]$trim)
Write-Host "[i] format: $fmt (trim=$trim)"

$outDir = Split-Path -Parent $OutPath
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$data = [CodeWalker.GameFiles.XmlMeta]::GetData($doc, $fmt, $outDir)
if ($null -eq $data -or $data.Length -eq 0) { throw "GetData bos dondu -- XML semasi ytyp degil olabilir" }
[IO.File]::WriteAllBytes($OutPath, $data)
Write-Host "[yazildi] $OutPath  ($($data.Length) bayt, zlib sikistirilmis)"

# --- GERI OKUMA: tek gecerli olcut ---
Write-Host ''
Write-Host '=== GERI OKUMA ==='
$bytes = [IO.File]::ReadAllBytes($OutPath)
$ytyp = New-Object CodeWalker.GameFiles.YtypFile
$ytyp.Load($bytes)      # tek argumanli overload: RpfFileEntry gerektirmez
$archs = $ytyp.AllArchetypes
if ($null -eq $archs -or $archs.Count -lt 1) {
    Write-Host 'DENETIM BASARISIZ: archetype okunamadi'
    exit 1
}
Write-Host "  archetype sayisi: $($archs.Count)"
foreach ($a in $archs) {
    $bd = $a._BaseArchetypeDef
    Write-Host ("  name={0}  assetName={1}  textureDict={2}  assetType={3}" -f `
        $a.Name, $bd.assetName, $bd.textureDictionary, $bd.assetType)
    Write-Host ("     lodDist={0}  flags={1}  bbMin=({2})  bbMax=({3})" -f `
        $bd.lodDist, $bd.flags, $bd.bbMin, $bd.bbMax)
}
Write-Host 'TUM DENETIMLER GECTI'
