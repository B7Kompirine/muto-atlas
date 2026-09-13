# build_procedural.ps1 - indexes procedural.meta (the procedural plant/object
# table).
#
# WHAT IT IS FOR: the 'Procedural ID' field of a Sollumz collision material and the
# grass batch names in CodeWalker come from here. It is the only source that tells
# you what grows on a ground collision for the number you write into it.
#
# * 'Procedural ID' = the INDEX INTO THE <procTagTable> LIST (0-based).
#    NOT <procObjInfos> -- they are two separate lists and their indexes do not match.
#    Verified: procTagTable[15] = Green_Meadow_Flowers,
#              procTagTable[38] = MOUNTAINSIDE_DRY
#    (both had been read independently from the Sollumz UI).
#
# A tag can point to either side:
#   procObjTag -> a SOLID OBJECT in <procObjInfos> (rock, litter, bush model)
#   plantTag   -> GRASS/PLANT in <plantInfos>      (drawn by a shader)
# If both are empty the index is unused (0 = 'null', 9 = '_EMPTY_DO_NOT_USE_').
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_procedural.ps1

param(
    [string] $GtaFolder,
    [string] $CodeWalker,
    [string] $Out
)

$ErrorActionPreference = 'Stop'

if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent) 'data' }
if (-not (Test-Path -LiteralPath $Out)) { New-Item -ItemType Directory -Path $Out | Out-Null }

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path -LiteralPath $CodeWalker)) {
    throw "CodeWalker.Core.dll not found. Pass it with -CodeWalker <path>."
}

$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V folder not found." }

$cwDir = Split-Path $CodeWalker -Parent
$script:cwDir = $cwDir
[System.AppDomain]::CurrentDomain.add_AssemblyResolve([System.ResolveEventHandler]{
    param($sender, $e)
    $short = ($e.Name -split ',')[0]
    $p = Join-Path $script:cwDir "$short.dll"
    if (Test-Path -LiteralPath $p) { return [System.Reflection.Assembly]::LoadFrom($p) }
    return $null
})

Add-Type -Path $CodeWalker -ErrorAction SilentlyContinue

Write-Output "CodeWalker : $CodeWalker"
Write-Output "GTA V      : $GtaFolder"

[CodeWalker.GameFiles.GTA5Keys]::LoadFromPath($GtaFolder, $null)
$man = New-Object CodeWalker.GameFiles.RpfManager
$man.Init($GtaFolder, {param($s)}, {param($s)}, $false, $true)

# The update.rpf version OVERRIDES common.rpf -- search it first.
$metaPaths = @(
    'update\update.rpf\common\data\materials\procedural.meta',
    'common.rpf\data\materials\procedural.meta'
)
$xml = $null
foreach ($metaPath in $metaPaths) {
    foreach ($rpf in $man.AllRpfs) {
        foreach ($e in $rpf.AllEntries) {
            $fe = $e -as [CodeWalker.GameFiles.RpfFileEntry]
            if ($fe -and $fe.Path -eq $metaPath) {
                $xml = [System.Text.Encoding]::UTF8.GetString($fe.File.ExtractFile($fe))
                Write-Output "Source     : $metaPath"
                break
            }
        }
        if ($xml) { break }
    }
    if ($xml) { break }
}
if (-not $xml) { throw "procedural.meta not found." }

# UTF8.GetString leaves the BOM (U+FEFF) at the start of the text and the [xml] cast
# crashes with "Cannot convert value". Trimming it is REQUIRED.
$xml = $xml.TrimStart([char]0xFEFF, [char]0xFFFE).Trim()
$doc = [xml]$xml

# procObjInfos: tag -> model list (several models can hang off one tag)
$objByTag = @{}
foreach ($it in $doc.CProceduralInfo.procObjInfos.Item) {
    $t = "$($it.Tag)".Trim()
    if (-not $t) { continue }
    if (-not $objByTag.ContainsKey($t)) { $objByTag[$t] = New-Object System.Collections.ArrayList }
    [void]$objByTag[$t].Add("$($it.ModelName)".Trim())
}

$rows = New-Object System.Collections.ArrayList
[void]$rows.Add("id`tname`tprocObjTag`tplantTag`tkind`tmodels")

$i = 0
$usedCount = 0
foreach ($it in $doc.CProceduralInfo.procTagTable.Item) {
    $name = "$($it.name)".Trim()
    $po   = "$($it.procObjTag)".Trim()
    $pl   = "$($it.plantTag)".Trim()

    # 'bos' (Turkish for "empty") stays as the kind value: assetdb.py compares the kind column against it.
    $kind = if ($po -and $pl) { 'obj+plant' }
            elseif ($po)      { 'obj' }
            elseif ($pl)      { 'plant' }
            else              { 'bos' }
    if ($kind -ne 'bos') { $usedCount++ }

    $models = ''
    if ($po -and $objByTag.ContainsKey($po)) {
        $models = ($objByTag[$po] | Select-Object -Unique) -join ','
    }

    [void]$rows.Add("$i`t$name`t$po`t$pl`t$kind`t$models")
    $i++
}

$outPath = Join-Path $Out 'procedural.tsv'
[IO.File]::WriteAllLines($outPath, $rows, (New-Object System.Text.UTF8Encoding($false)))

Write-Output "[+] $outPath"
Write-Output "[+] $i procedural IDs ($usedCount of them filled), $($objByTag.Count) distinct procObj tags"
