# build_procedural.ps1 — procedural.meta'yi (prosedurel bitki/obje tablosu)
# indeksler.
#
# NE ISE YARAR: Sollumz collision materyalindeki 'Procedural ID' alani ile
# CodeWalker'daki grass batch adlari buradan gelir. Bir zemin collision'ina
# hangi sayiyi yazarsan orada ne bitecegini soyleyen tek kaynak budur.
#
# ⭐ 'Procedural ID' = <procTagTable> LISTESININ INDEKSIDIR (0 tabanli).
#    <procObjInfos> DEGIL -- ikisi ayri listedir ve indeksleri tutmaz.
#    Dogrulandi: procTagTable[15] = Green_Meadow_Flowers,
#                procTagTable[38] = MOUNTAINSIDE_DRY
#    (ikisi de bagimsiz olarak Sollumz arayuzunden okunmustu).
#
# Bir tag iki tarafa da bakabilir:
#   procObjTag -> <procObjInfos> icindeki KATI OBJE (tas, cop, cali modeli)
#   plantTag   -> <plantInfos>   icindeki CIM/BITKI (shader'la cizilen)
# Ikisi bos ise o indeks kullanilmiyordur (0 = 'null', 9 = '_EMPTY_DO_NOT_USE_').
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_procedural.ps1

param(
    [string] $GtaFolder,
    [string] $CodeWalker,
    [string] $Out
)

$ErrorActionPreference = 'Stop'

if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent) 'data' }
if (-not (Test-Path -LiteralPath $Out)) { New-Item -ItemType Directory -Path $Out | Out-Null }

if (-not $CodeWalker) {
    $cands = @(
        "$env:USERPROFILE\Desktop\FiveM\CodeWalker30_dev46\CodeWalker.Core.dll",
        "$env:USERPROFILE\Desktop\CodeWalker\CodeWalker.Core.dll"
    )
    $CodeWalker = $cands | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $CodeWalker -or -not (Test-Path -LiteralPath $CodeWalker)) {
    throw "CodeWalker.Core.dll bulunamadi. -CodeWalker <yol> ile ver."
}

if (-not $GtaFolder) {
    $cands = @(
        "C:\Program Files\Epic Games\GTAV",
        "C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V",
        "C:\Program Files\Rockstar Games\Grand Theft Auto V"
    )
    $GtaFolder = $cands | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $GtaFolder) { throw "GTA V klasoru bulunamadi." }

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

# update.rpf surumu common.rpf'i EZER -- once onu ara.
$yollar = @(
    'update\update.rpf\common\data\materials\procedural.meta',
    'common.rpf\data\materials\procedural.meta'
)
$xml = $null
foreach ($yol in $yollar) {
    foreach ($rpf in $man.AllRpfs) {
        foreach ($e in $rpf.AllEntries) {
            $fe = $e -as [CodeWalker.GameFiles.RpfFileEntry]
            if ($fe -and $fe.Path -eq $yol) {
                $xml = [System.Text.Encoding]::UTF8.GetString($fe.File.ExtractFile($fe))
                Write-Output "Kaynak     : $yol"
                break
            }
        }
        if ($xml) { break }
    }
    if ($xml) { break }
}
if (-not $xml) { throw "procedural.meta bulunamadi." }

# UTF8.GetString BOM'u (U+FEFF) metnin basinda birakir ve [xml] cast'i
# "Cannot convert value" ile coker. Kirpilmasi SART.
$xml = $xml.TrimStart([char]0xFEFF, [char]0xFFFE).Trim()
$doc = [xml]$xml

# procObjInfos: tag -> model listesi (bir tag'e birden fazla model asilabilir)
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
$kullanilan = 0
foreach ($it in $doc.CProceduralInfo.procTagTable.Item) {
    $name = "$($it.name)".Trim()
    $po   = "$($it.procObjTag)".Trim()
    $pl   = "$($it.plantTag)".Trim()

    $kind = if ($po -and $pl) { 'obj+plant' }
            elseif ($po)      { 'obj' }
            elseif ($pl)      { 'plant' }
            else              { 'bos' }
    if ($kind -ne 'bos') { $kullanilan++ }

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
Write-Output "[+] $i procedural ID ($kullanilan tanesi dolu), $($objByTag.Count) farkli procObj tag"
