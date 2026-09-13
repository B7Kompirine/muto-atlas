# ytd_find.ps1 - scans ALL .ytd names in the game and matches them by jenkins hash.
#
# WHY: an archetype's textureDictionary field is stored as a hash; without knowing the
# name you cannot tell which dictionary to extract.
#
# Usage:
#   pwsh ytd_find.ps1 -Hash 232020629 -GtaFolder 'C:\...\GTAV'
#
# Details: branches/map/vanilla-part-replacement.md section 4

param([Parameter(Mandatory=$true)][uint32]$Hash,[string]$GtaFolder,[string]$CodeWalker)
$ErrorActionPreference='Stop'
# !! `.gta` was written here once; the config key is `gtaFolder`. PowerShell gives
#    no error for a missing property, it returns $null -> the configuration was SILENTLY
#    ignored and it fell back to hard-coded guesses. Key names now live in one place in paths.ps1.
$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if(-not $CodeWalker){ throw "CodeWalker.Core.dll not found. python assetdb.py path codewalker ""<path>""" }
Add-Type -Path $CodeWalker
$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if(-not $GtaFolder){ throw "GTA V folder not found. python assetdb.py path gta ""<path>""" }
Write-Host "[i] GTA: $GtaFolder"
$rm=New-Object CodeWalker.GameFiles.RpfManager
$rm.Init($GtaFolder,{param($s)},{param($s)},$false,$false)
$hits=@()
foreach($rpf in $rm.AllRpfs){
  foreach($e in $rpf.AllEntries){
    if($e.NameLower -like '*.ytd'){
      $n=[System.IO.Path]::GetFileNameWithoutExtension($e.NameLower)
      if([CodeWalker.GameFiles.JenkHash]::GenHash($n) -eq $Hash){ $hits+= "$n   ($($rpf.Path))" }
    }
  }
}
if($hits){ Write-Host "[+] MATCHES:"; $hits|select -First 8|%{Write-Host "    $_"} } else { Write-Host "[!] no match" }
