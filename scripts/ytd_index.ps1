# ytd_index.ps1 - lists the texture NAMES of all .ytd files in a folder (writes no DDS).
#
# WHY: vanilla map/prop models have NO EMBEDDED textures; all of them use an external
# dictionary + the gtxd parent chain. Instead of guessing which dictionary a texture
# is in, build an index.
#
# Usage:
#   pwsh ytd_index.ps1 -Roots @('C:\extracted\ytd') -Out idx.tsv
# Output: every line  "<texture name>	<ytd file name>"
#
# Details: branches/map/vanilla-part-replacement.md section 4

param([Parameter(Mandatory=$true)][string[]]$Roots,[Parameter(Mandatory=$true)][string]$Out,
      [string]$CodeWalker)
$ErrorActionPreference='Stop'
$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
# Guard: Add-Type -Path $null says "argument is null" and the reason is lost.
if(-not $CodeWalker -or -not (Test-Path $CodeWalker)){ throw "CodeWalker.Core.dll not found. Pass the path with -CodeWalker." }
Add-Type -Path $CodeWalker
$sw=[System.IO.StreamWriter]::new($Out)
$n=0; $failCount=0; $firstError=$null
foreach($r in $Roots){
  Get-ChildItem -LiteralPath $r -Recurse -Filter *.ytd -File | ForEach-Object {
    try{
      $d=[System.IO.File]::ReadAllBytes($_.FullName)
      $e=[CodeWalker.GameFiles.RpfFile]::CreateResourceFileEntry([ref]$d,0)
      $dd=[CodeWalker.GameFiles.ResourceBuilder]::Decompress($d)
      $y=New-Object CodeWalker.GameFiles.YtdFile
      $y.Load($dd,$e)
      $td=$y.TextureDict
      if($td -and $td.Textures -and $td.Textures.data_items){
        foreach($t in $td.Textures.data_items){ $sw.WriteLine("$($t.Name)`t$($_.Name)") }
      }
      $n++
    }catch{ $failCount++; if(-not $firstError){ $firstError="$($_.Exception.Message) ($($_.TargetObject))" } }
  }
}
$sw.Close()
Write-Host "[=] $n ytd read, $failCount errors -> $Out"
# Do not swallow the reason: if all of them fail, "0 read" alone does not say what broke.
if($failCount -gt 0){ Write-Host "[!] first error: $firstError" }
