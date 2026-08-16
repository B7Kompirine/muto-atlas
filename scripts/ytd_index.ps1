# ytd_index.ps1 - bir klasordeki tum .ytd'lerin doku ADLARINI listeler (DDS yazmaz).
#
# NEDEN: vanilla harita/prop modellerinde GOMULU doku yoktur; hepsi dis
# sozluk + gtxd ebeveyn zinciri kullanir. Bir dokunun hangi sozlukte
# oldugunu tahmin etmek yerine indeks cikar.
#
# Kullanim:
#   pwsh ytd_index.ps1 -Roots @('C:\cikarilan\ytd') -Cikti idx.tsv
# Cikti: her satir  "<doku adi>	<ytd dosya adi>"
#
# Ayrinti: references/vanilla-parca-degistirme.md §4

param([Parameter(Mandatory=$true)][string[]]$Roots,[Parameter(Mandatory=$true)][string]$Out,
      [string]$CodeWalker)
$ErrorActionPreference='Stop'
$CodeWalker = & "$PSScriptRoot\yol.ps1" codewalker $CodeWalker
# Guard: Add-Type -Path $null "argument is null" der ve sebep kaybolur.
if(-not $CodeWalker -or -not (Test-Path $CodeWalker)){ throw "CodeWalker.Core.dll bulunamadi. -CodeWalker ile yol ver." }
Add-Type -Path $CodeWalker
$sw=[System.IO.StreamWriter]::new($Out)
$n=0; $hata=0; $ilkHata=$null
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
    }catch{ $hata++; if(-not $ilkHata){ $ilkHata="$($_.Exception.Message) ($($_.TargetObject))" } }
  }
}
$sw.Close()
Write-Host "[=] $n ytd okundu, $hata hata -> $Out"
# Sebebi yutma: hepsi duserse "0 okundu" tek basina neyin bozuldugunu soylemez.
if($hata -gt 0){ Write-Host "[!] ilk hata: $ilkHata" }
