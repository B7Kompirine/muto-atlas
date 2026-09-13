# meta_xml_to_bin.ps1 - .ytyp.xml / .ymap.xml -> game-ready binary.
#
# WHY A SEPARATE TOOL: xml_to_res.ps1 in muto-atlas only knows resource (RSC)
# types (.yft .ydd .ydr .ybn .ypt .ytd ...); .ytyp and .ymap are NOT
# there. Both are written through MetaFormat.RSC with XmlMeta.GetData.
#
# MEASURED: for des_protree.ytyp the XML -> binary -> XML round trip came out
# IDENTICAL across all 4,978 bytes (compositeEntityTypes / Animations /
# effectsData included). So the round trip is lossless.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File meta_xml_to_bin.ps1 -XmlPath x.ytyp.xml
#   ... -XmlPath x.ymap.xml -OutPath other\place\x.ymap

param(
    [Parameter(Mandatory=$true)][string] $XmlPath,
    [string] $OutPath,
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

# If the path contains square brackets such as [script], Test-Path reads them as a wildcard.
if (-not (Test-Path -LiteralPath $XmlPath)) { throw "XML not found: $XmlPath" }
if (-not $OutPath) { $OutPath = $XmlPath -replace '\.xml$', '' }

if (-not $CodeWalker) {
    $CodeWalker = @(
        "$env:USERPROFILE\Desktop\CodeWalker\CodeWalker.Core.dll"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $CodeWalker) { throw "CodeWalker.Core.dll not found." }

Add-Type -Path $CodeWalker
$asm = [System.Reflection.Assembly]::LoadFrom($CodeWalker)
$mf  = $asm.GetType('CodeWalker.GameFiles.MetaFormat')

$ext = [System.IO.Path]::GetExtension($OutPath).ToLowerInvariant()
if ($ext -ne '.ytyp' -and $ext -ne '.ymap' -and $ext -ne '.ymt') {
    throw "Unsupported extension '$ext'. This tool only writes .ytyp / .ymap / .ymt."
}

$doc = New-Object System.Xml.XmlDocument
$doc.Load((Resolve-Path -LiteralPath $XmlPath))

$folder = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($XmlPath))
$data = [CodeWalker.GameFiles.XmlMeta]::GetData($doc, [Enum]::Parse($mf, 'RSC'), $folder)
if (-not $data) { throw "XmlMeta.GetData returned null -- the XML structure may be broken." }

[System.IO.File]::WriteAllBytes($OutPath, $data)

# READ BACK. Size is NOT a validity measure (RSC7 is zlib compressed);
# the only valid measure is reading it back.
if ($ext -eq '.ymt') {
    # CPedVariationInfo etc. is RSC meta. Read it back and print the meta block count.
    $y = New-Object CodeWalker.GameFiles.YmtFile
    $y.Load([System.IO.File]::ReadAllBytes($OutPath))
    $root = if ($y.Meta -and $y.Meta.DataBlocks) { $y.Meta.DataBlocks.Count } else { 0 }
    Write-Host ("[+] {0}  {1} bytes  -> meta blocks={2}" -f [System.IO.Path]::GetFileName($OutPath), $data.Length, $root)
    if ($root -eq 0) { Write-Host "[!] meta blocks 0 -- the file was written empty."; exit 1 }
} elseif ($ext -eq '.ytyp') {
    $y = New-Object CodeWalker.GameFiles.YtypFile
    $y.Load([System.IO.File]::ReadAllBytes($OutPath))
    $na = if ($y.AllArchetypes) { $y.AllArchetypes.Count } else { 0 }
    $nc = if ($y.CompositeEntityTypes) { $y.CompositeEntityTypes.Count } else { 0 }
    Write-Host ("[+] {0}  {1} bytes  -> archetype={2}  compositeEntityTypes={3}" -f `
        [System.IO.Path]::GetFileName($OutPath), $data.Length, $na, $nc)
    if ($na -eq 0) { Write-Host "[!] archetype 0 -- the file was written empty."; exit 1 }
} else {
    $d = [System.IO.File]::ReadAllBytes($OutPath)
    $e = [CodeWalker.GameFiles.RpfFile]::CreateResourceFileEntry([ref]$d, 0)
    $d = [CodeWalker.GameFiles.ResourceBuilder]::Decompress($d)
    $y = New-Object CodeWalker.GameFiles.YmapFile
    $y.Load($d, $e)
    $ents = $y.AllEntities; if (-not $ents) { $ents = $y.RootEntities }
    $n = if ($ents) { $ents.Count } else { 0 }

    # !! LOSS GATE. XmlMeta.GetData DROPS entities in SOME ymaps and
    # silently returns success. Measured: hw1_rd_critical_1.ymap went 457 -> 128 even in a
    # round trip that did NOT TOUCH the file AT ALL. Had it been shipped, the 325
    # objects in that area (trees, signs, traffic lights, bins) would have silently vanished.
    # So no file is left behind without comparing against the Item count in the XML.
    $xmlCount = $doc.SelectNodes('//entities/Item').Count
    Write-Host ("[+] {0}  {1} bytes  -> entity={2} (XML {3})  parent={4}" -f `
        [System.IO.Path]::GetFileName($OutPath), $data.Length, $n, $xmlCount, $y.CMapData.parent)
    if ($n -eq 0) { Write-Host "[!] entity 0 -- the file was written empty."; exit 1 }
    if ($xmlCount -gt 0 -and $n -ne $xmlCount) {
        Write-Host ("[!] LOSS: XML {0} entities, binary {1}. This file does NOT pass the XML round trip" -f $xmlCount, $n)
        Write-Host    "    LOSSLESSLY -- do not ship it. Use YmapFile.RemoveEntity + YmapFile.Save()"
        Write-Host    "    instead (measured lossless on the same file)."
        Remove-Item -LiteralPath $OutPath -Force
        exit 1
    }
}
