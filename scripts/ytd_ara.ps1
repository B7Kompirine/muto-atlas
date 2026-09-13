# ytd_ara.ps1 - oyundaki TUM .ytd adlarini tarar, jenkins hash ile eslestirir.
#
# NEDEN: arketipin textureDictionary alani hash olarak durur; adi bilinmeden
# hangi sozlugun cikarilacagi bilinmez.
#
# Kullanim:
#   pwsh ytd_ara.ps1 -Hash 232020629 -GtaFolder 'C:\...\GTAV'
#
# Ayrinti: dallar/map/vanilla-parca-degistirme.md §4

param([Parameter(Mandatory=$true)][uint32]$Hash,[string]$GtaFolder,[string]$CodeWalker)
$ErrorActionPreference='Stop'
# ⛔ Burada bir kez `.gta` yazilmisti; config anahtari `gtaFolder`. PowerShell
#    olmayan property'de hata vermez, $null doner -> yapilandirma SESSIZCE yok
#    sayilip sabit tahminlere dusuyordu. Anahtar adlari artik yol.ps1'de tek yerde.
$CodeWalker = & "$PSScriptRoot\yol.ps1" codewalker $CodeWalker
if(-not $CodeWalker){ throw "CodeWalker.Core.dll bulunamadi. python assetdb.py yol codewalker ""<yol>""" }
Add-Type -Path $CodeWalker
$GtaFolder = & "$PSScriptRoot\yol.ps1" gta $GtaFolder
if(-not $GtaFolder){ throw "GTA V klasoru bulunamadi. python assetdb.py yol gta ""<yol>""" }
Write-Host "[i] GTA: $GtaFolder"
$rm=New-Object CodeWalker.GameFiles.RpfManager
$rm.Init($GtaFolder,{param($s)},{param($s)},$false,$false)
$bul=@()
foreach($rpf in $rm.AllRpfs){
  foreach($e in $rpf.AllEntries){
    if($e.NameLower -like '*.ytd'){
      $n=[System.IO.Path]::GetFileNameWithoutExtension($e.NameLower)
      if([CodeWalker.GameFiles.JenkHash]::GenHash($n) -eq $Hash){ $bul+= "$n   ($($rpf.Path))" }
    }
  }
}
if($bul){ Write-Host "[+] ESLESEN:"; $bul|select -First 8|%{Write-Host "    $_"} } else { Write-Host "[!] eslesme yok" }
