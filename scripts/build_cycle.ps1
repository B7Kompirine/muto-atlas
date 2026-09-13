# build_cycle.ps1 — hava timecycle dosyalarini oyunun kendi arsivinden cikarir.
#
# NEDEN CIKARIYORUZ, GOMMUYORUZ
# =============================
# w_*.xml ve time.xml Rockstar dosyalaridir. Katmanin icine gomulmezler;
# kullanicinin kendi kurulumundan uretilirler. Dagitilan sey bu betiktir.
#
# CIKTI
#   data/timecycle/w_*.xml     17 hava cycle'i
#   data/timecycle/time.xml    13 keyframe'in saat cizelgesi
#
# NOT: time.xml IKI kere gecer. Bize lazim olan levels/gta5 altindaki
# 13 sample'lik olan; data/time.xml 4 sample'lik baska bir dosyadir.
#
# KULLANIM
#   powershell -File build_cycle.ps1
#   powershell -File build_cycle.ps1 -GtaFolder "C:\...\GTAV" -CodeWalker "...\CodeWalker.Core.dll"

param(
  [string] $GtaFolder,
  [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path -LiteralPath $CodeWalker)) {
  throw "CodeWalker.Core.dll bulunamadi. -CodeWalker ile yolunu ver."
}

$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V klasoru bulunamadi. -GtaFolder ile yolunu ver." }

$outDir = Join-Path (Split-Path (Split-Path $PSCommandPath -Parent) -Parent) 'data\timecycle'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Output "CodeWalker : $CodeWalker"
Write-Output "GTA V      : $GtaFolder"
Write-Output "Cikti      : $outDir"

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

# CodeWalker surumleri arasinda imza degisiyor: eski surumde
# LoadFromPath(path, key) / Init(folder, cb, cb, bool, bool), yenisinde araya
# bir `gen9` bool giriyor. Imzayi VARSAYMA, parametre sayisina gore sec.
$isEnhanced = Test-Path -LiteralPath (Join-Path $GtaFolder 'GTA5_Enhanced.exe')
$keys = $asm.GetType('CodeWalker.GameFiles.GTA5Keys')
$lm = $keys.GetMethods('Public,Static') | Where-Object { $_.Name -eq 'LoadFromPath' } |
      Sort-Object { $_.GetParameters().Count } | Select-Object -Last 1
$lp = $lm.GetParameters().Count
if ($lp -eq 3) { $lm.Invoke($null, @($GtaFolder, $isEnhanced, '')) }
else           { $lm.Invoke($null, @($GtaFolder, '')) }
Write-Output "[+] anahtarlar yuklendi (gen9=$isEnhanced)"

$man = [Activator]::CreateInstance($asm.GetType('CodeWalker.GameFiles.RpfManager'))
$im = $man.GetType().GetMethods() | Where-Object { $_.Name -eq 'Init' } |
      Sort-Object { $_.GetParameters().Count } | Select-Object -Last 1
$cb = [Action[string]] {}
if ($im.GetParameters().Count -eq 6) { $im.Invoke($man, @($GtaFolder, $isEnhanced, $cb, $cb, $false, $false)) }
else                                 { $im.Invoke($man, @($GtaFolder, $cb, $cb, $false, $false)) }
Write-Output "[+] arsivler tarandi: $($man.AllRpfs.Count) rpf"

# w_*.xml — ayni ad birden cok arsivde olabilir, update.rpf tabani ezer
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
Write-Output "[+] $n hava cycle'i yazildi"

# time.xml: 13 sample'lik OLAN lazim, 4 sample'lik olan degil
$best = $null
foreach ($rpf in $man.AllRpfs) {
  foreach ($e in $rpf.AllEntries) {
    if ($e.Name -eq 'time.xml' -and $e.Path -like '*levels*') { $best = $e.Path }
  }
}
if (-not $best) { throw "levels/gta5/time.xml bulunamadi — saat cizelgesi olmadan cycle degerlendirilemez." }
$txt = $man.GetFileUTF8Text($best)
[IO.File]::WriteAllText((Join-Path $outDir 'time.xml'), $txt, [Text.Encoding]::UTF8)
$samples = ([regex]::Matches($txt, '<sample\b')).Count
Write-Output "[+] time.xml yazildi ($best, $samples sample)"
if ($samples -lt 10) {
  Write-Warning "sample sayisi $samples — 13 bekleniyordu. Yanlis time.xml alinmis olabilir."
}
Write-Output ""
Write-Output "Dogrula: python assetdb.py cycle w_clear --saat 20"
