# build_cycle.ps1 - extracts the weather timecycle files from the game's own archives.
#
# WHY WE EXTRACT THEM INSTEAD OF BUNDLING THEM
# ============================================
# w_*.xml and time.xml are Rockstar files. They are not bundled into the layer;
# they are generated from the user's own install. What is distributed is this script.
#
# OUTPUT
#   data/timecycle/w_*.xml     17 weather cycles
#   data/timecycle/time.xml    the hour schedule of the 13 keyframes
#
# NOTE: time.xml appears TWICE. The one we need is the 13-sample file under
# levels/gta5; data/time.xml is a different file with 4 samples.
#
# USAGE
#   powershell -File build_cycle.ps1
#   powershell -File build_cycle.ps1 -GtaFolder "C:\...\GTAV" -CodeWalker "...\CodeWalker.Core.dll"

param(
  [string] $GtaFolder,
  [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path -LiteralPath $CodeWalker)) {
  throw "CodeWalker.Core.dll not found. Pass its path with -CodeWalker."
}

$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V folder not found. Pass its path with -GtaFolder." }

$outDir = Join-Path (Split-Path (Split-Path $PSCommandPath -Parent) -Parent) 'data\timecycle'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Output "CodeWalker : $CodeWalker"
Write-Output "GTA V      : $GtaFolder"
Write-Output "Output     : $outDir"

$cwDir = Split-Path $CodeWalker -Parent
$onResolve = [System.ResolveEventHandler] {
  param($sender, $e)
  $short = ($e.Name -split ',')[0]
  $p = Join-Path $script:cwDir "$short.dll"
  if (Test-Path -LiteralPath $p) { return [System.Reflection.Assembly]::LoadFrom($p) }
  return $null
}
$script:cwDir = $cwDir
[System.AppDomain]::CurrentDomain.add_AssemblyResolve($onResolve)
$asm = [Reflection.Assembly]::LoadFrom($CodeWalker)

# The signature changes between CodeWalker versions: older versions have
# LoadFromPath(path, key) / Init(folder, cb, cb, bool, bool), newer ones insert
# a `gen9` bool. Do NOT ASSUME the signature; pick it by parameter count.
$isEnhanced = Test-Path -LiteralPath (Join-Path $GtaFolder 'GTA5_Enhanced.exe')
$keys = $asm.GetType('CodeWalker.GameFiles.GTA5Keys')
$lm = $keys.GetMethods('Public,Static') | Where-Object { $_.Name -eq 'LoadFromPath' } |
      Sort-Object { $_.GetParameters().Count } | Select-Object -Last 1
$lp = $lm.GetParameters().Count
if ($lp -eq 3) { $lm.Invoke($null, @($GtaFolder, $isEnhanced, '')) }
else           { $lm.Invoke($null, @($GtaFolder, '')) }
Write-Output "[+] keys loaded (gen9=$isEnhanced)"

$man = [Activator]::CreateInstance($asm.GetType('CodeWalker.GameFiles.RpfManager'))
$im = $man.GetType().GetMethods() | Where-Object { $_.Name -eq 'Init' } |
      Sort-Object { $_.GetParameters().Count } | Select-Object -Last 1
$cb = [Action[string]] {}
if ($im.GetParameters().Count -eq 6) { $im.Invoke($man, @($GtaFolder, $isEnhanced, $cb, $cb, $false, $false)) }
else                                 { $im.Invoke($man, @($GtaFolder, $cb, $cb, $false, $false)) }
Write-Output "[+] archives scanned: $($man.AllRpfs.Count) rpf"

# w_*.xml - the same name can be in several archives; update.rpf overrides the base
$pick = @{}
foreach ($rpf in $man.AllRpfs) {
  foreach ($e in $rpf.AllEntries) {
    if ($e.Name -and $e.Name -like 'w_*.xml' -and $e.Path -like '*timecycle*') {
      $pri = if ($e.Path -like 'update*') { 2 } else { 1 }
      if (-not $pick.ContainsKey($e.Name) -or $pick[$e.Name].pri -lt $pri) {
        $pick[$e.Name] = @{ pri = $pri; path = $e.Path }
      }
    }
  }
}
$n = 0
foreach ($k in $pick.Keys) {
  $txt = $man.GetFileUTF8Text($pick[$k].path)
  if ($txt) { [IO.File]::WriteAllText((Join-Path $outDir $k), $txt, [Text.Encoding]::UTF8); $n++ }
}
Write-Output "[+] $n weather cycles written"

# time.xml: the one WITH 13 samples is needed, not the 4-sample one
$best = $null
foreach ($rpf in $man.AllRpfs) {
  foreach ($e in $rpf.AllEntries) {
    if ($e.Name -eq 'time.xml' -and $e.Path -like '*levels*') { $best = $e.Path }
  }
}
if (-not $best) { throw "levels/gta5/time.xml not found - cycles cannot be evaluated without the hour schedule." }
$txt = $man.GetFileUTF8Text($best)
[IO.File]::WriteAllText((Join-Path $outDir 'time.xml'), $txt, [Text.Encoding]::UTF8)
$samples = ([regex]::Matches($txt, '<sample\b')).Count
Write-Output "[+] time.xml written ($best, $samples samples)"
if ($samples -lt 10) {
  Write-Warning "sample count $samples - 13 expected. The wrong time.xml may have been picked."
}
Write-Output ""
Write-Output "Verify: python assetdb.py cycle w_clear --hour 20"
