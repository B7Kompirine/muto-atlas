# paths.ps1 - resolves external tool paths from data/config.json (the PowerShell side).
#
# WHY: the same paths were scattered across scripts (29 hard-coded guesses for
# CodeWalker, 23 for GTA). When a user installed a tool somewhere else, every one
# of them had to be fixed by hand. This reads the SAME registry as the Python
# side: paths.py.
#
# !! PowerShell returns $null for a missing property, without an error. That is
#    why the key names live in ONE place here: a misspelled key would look like
#    "no configuration" and silently fall back to a hard-coded guess --
#    exactly what happened in ytd_find.ps1 (`gta` instead of `gtaFolder`).
#
# TWO WAYS TO USE IT:
#
#   1) CALL IT (one line, the common case):
#        $CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
#        $GtaFolder  = & "$PSScriptRoot\paths.ps1" gta        $GtaFolder
#      Returns NOTHING when the path is not found; the caller reports its own error.
#
#   2) DOT-SOURCE IT (when several paths are needed):
#        . (Join-Path $PSScriptRoot 'paths.ps1')
#        $CodeWalker = Resolve-MutoPath codewalker $CodeWalker
#
# param() must be the FIRST statement of a script, so a dot-source cannot come
# before param(). That is why form 1 exists.

$script:MutoConfig = Join-Path (Split-Path $PSScriptRoot -Parent) 'data\config.json'

$script:MutoPaths = @{
  codewalker = @{
    key = 'codeWalker'; kind = 'file'
    candidates = @(
      "$env:USERPROFILE\Desktop\CodeWalker\CodeWalker.Core.dll")
  }
  gta = @{
    key = 'gtaFolder'; kind = 'folder'
    candidates = @(
      'C:\Program Files\Rockstar Games\Grand Theft Auto V',
      'C:\Program Files\Epic Games\GTAV',
      'C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V',
      'C:\SteamLibrary\steamapps\common\Grand Theft Auto V',
      'D:\SteamLibrary\steamapps\common\Grand Theft Auto V',
      'E:\Grand Theft Auto V')
  }
  server  = @{ key = 'resources'; kind = 'folder'; candidates = @() }
  blender = @{ key = 'blender';   kind = 'file';   candidates = @() }
}

# Old Turkish names keep working.
$script:MutoPathAliases = @{ sunucu = 'server' }

function Get-MutoConfig {
    if (-not (Test-Path -LiteralPath $script:MutoConfig)) { return @{} }
    try { return (Get-Content -LiteralPath $script:MutoConfig -Raw | ConvertFrom-Json) }
    catch { return @{} }
}

function Test-MutoPath([string]$Path, [string]$Kind) {
    if (-not $Path) { return $false }
    # Paths with square brackets need -LiteralPath, otherwise they are read as wildcards.
    if ($Kind -eq 'folder') { return (Test-Path -LiteralPath $Path -PathType Container) }
    return (Test-Path -LiteralPath $Path -PathType Leaf)
}

function Resolve-MutoPath {
    <#
      Order: explicitly given (-Given) -> config.json -> known candidates.
      Returns $null when nothing is found; the caller MUST report an error, not carry on silently.
    #>
    param(
        [Parameter(Mandatory=$true)][Alias('Ad')][string]$Name,
        [Alias('Verilen')][string]$Given
    )
    if ($Given) { return $Given }
    $n = $Name.ToLower()
    if ($script:MutoPathAliases.ContainsKey($n)) { $n = $script:MutoPathAliases[$n] }
    $entry = $script:MutoPaths[$n]
    if ($entry) { $keys = @($entry.key); $kind = $entry.kind }
    else { $keys = @("path_$n", "yol_$n"); $kind = 'file' }

    $cfg = Get-MutoConfig
    # Ask whether the property EXISTS: a missing property returns $null and the reason is lost.
    $stored = $null
    $storedKey = $null
    foreach ($k in $keys) {
        if (-not $stored -and $cfg -and $cfg.PSObject.Properties[$k]) {
            $stored = $cfg.PSObject.Properties[$k].Value
            $storedKey = $k
        }
    }
    if ($stored) {
        if (Test-MutoPath $stored $kind) { return $stored }
        Write-Host "[!] '$storedKey' is set in config.json but MISSING on disk: $stored"
    }
    if ($entry) {
        foreach ($c in $entry.candidates) { if (Test-MutoPath $c $kind) { return $c } }
    }
    return $null
}

function Resolve-MutoPathRequired {
    param([Parameter(Mandatory=$true)][Alias('Ad')][string]$Name, [Alias('Verilen')][string]$Given)
    $p = Resolve-MutoPath -Name $Name -Given $Given
    if (-not $p) {
        throw ("Path '$Name' not found. Set it with:  python assetdb.py path $Name ""<path>""")
    }
    return $p
}

# --- WHEN CALLED: print the path. When dot-sourced, $args is empty and this block
#     does not run, so the two ways of using the script do not collide.
if ($args.Count -ge 1) {
    Resolve-MutoPath -Name $args[0] -Given $(if ($args.Count -ge 2) { $args[1] } else { $null })
}
