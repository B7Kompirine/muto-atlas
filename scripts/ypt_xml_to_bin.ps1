# ypt_xml_to_bin.ps1 - .ypt.xml -> binary .ypt (with the CodeWalker bug patched).
#
# !! WHY A SEPARATE SCRIPT: CodeWalker's XML reader NEVER WRITES the `FxcFileHash`
#    field. Measured -- with an untouched vanilla file:
#
#      cut_arena.ypt  binary read      -> FxcFileHash = 246470498
#      same file      XML round trip   -> FxcFileHash = 0
#
#    So the problem is not in our XML, it is in the tool itself; EVERY .ypt built
#    from XML comes out without a shader. The `FxcFile` text looks right, the hash is
#    zero, and the hash is what the engine looks at. Symptom: the file is valid, the
#    `.ypt` loads, StartParticleFx* returns a NON-ZERO handle and NOTHING HAPPENS
#    ON SCREEN. No other check catches this symptom.
#
#    The fix is JenkHash: GenHash('ptfx_sprite') = 246470498, identical to the vanilla
#    binary value. `FxcTechniqueHash` is 0 in vanilla too -- do not touch it.
#
# Usage:
#   powershell -File ypt_xml_to_bin.ps1 -Xml <path\name.ypt.xml> [-Out <path\name.ypt>]
#   (The DDS files must be IN THE SAME FOLDER as the XML.)

param(
    [Parameter(Mandatory = $true)][string] $Xml,
    [string] $Out,
    [string] $Deploy,          # target stream/ folder (optional)
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker) { throw "CodeWalker.Core.dll not found" }
[Reflection.Assembly]::LoadFrom($CodeWalker) | Out-Null

if (-not (Test-Path -LiteralPath $Xml)) { throw "XML not found: $Xml" }
$xmlFolder = Split-Path -Parent (Resolve-Path -LiteralPath $Xml)
if (-not $Out) { $Out = ($Xml -replace '\.ypt\.xml$', '.ypt') }

# --- 1) XML -> object tree ---
$doc = New-Object System.Xml.XmlDocument
$doc.Load((Resolve-Path -LiteralPath $Xml))
$ypt = [CodeWalker.GameFiles.XmlYpt]::GetYpt($doc, $xmlFolder)

# --- 1b) VFT: the CodeWalker XML reader writes a VFT to NO block ---
#
# !! VFT = the object's class identity (vtable). Left at zero, the engine cannot
#    resolve the block's TYPE. The symptom is sneaky: the effect loads, particles draw,
#    but class-specific behaviour does not work. Measured case: the sprite sheet
#    texture is NOT SLICED -- all four cells of a 2x2 sheet are drawn onto one quad.
#    The same rule sliced correctly with the vanilla texture; the only difference was the VFT.
#
# The values were measured from core.ypt and EVERY TYPE CARRIES ONE VALUE, zero deviation:
#   Textures 107/107, EffectRules 964/964, EmitterRules 1993/1993,
#   ParticleRules 1736/1736, EventEmitter 2543/2543, KeyframeProp 4820/4820,
#   behaviours 1 value per type, domains 1 value per shape
$VFT_BLOCK = @{
    EffectRuleDict   = 1080048016; EmitterRuleDict = 1080048056
    ParticleRuleDict = 1080048096; Texture         = 1080137320
    EffectRule       = 1080081688; EmitterRule     = 1080083608
    ParticleRule     = 1080085192; EventEmitter    = 1080100952
    KeyframeProp     = 1080085392
}
$VFT_BEHAVIOUR = @{
    Acceleration = 1080066920; Age        = 1080067288; AnimateTexture = 1080068072
    Attractor    = 1080068456; Collision  = 1080069256; Colour         = 1080070168
    Dampening    = 1080070840; Decal      = 1080170408; DecalPool      = 1080170920
    FogVolume    = 1080172152; Light      = 1080174040; Liquid         = 1080174872
    MatrixWeight = 1080071352; Model      = 1080077240; Noise          = 1080072136
    River        = 1080175208; Rotation   = 1080073832; Size           = 1080074648
    Sprite       = 1080076760; Trail      = 1080078056; Velocity       = 1080075080
    Wind         = 1080075768; ZCull      = 1080175704
}
$VFT_DOMAIN = @{ Sphere = 1080088936; Box = 1080088880
                 Cylinder = 1080088992; Attractor = 1080089048 }
# !! ShaderVars entries have their own VFT too -- and this is the object that
#    MAKES THE TEXTURE BINDING (Type=Texture). Left at zero, the texture binds and
#    draws but sheet slicing does not work. Measured: Texture 5108/5108, Vector2
#    18846/18846, Keyframe 10216/10216 -- one value per type.
#    Vector4 and Vector2 SHARE the same VFT (1080097368).
$VFT_SHADERVAR = @{
    Texture = 1080097544; Vector2 = 1080097368
    Vector4 = 1080097368; Keyframe = 1080097256
}

$vftN = 0
function Vft($o, $value) {
    if ($null -eq $o -or $null -eq $value) { return }
    if ([uint32]$o.VFT -ne [uint32]$value) { $o.VFT = [uint32]$value; $script:vftN++ }
}

# !! `FileVFT` IS A SEPARATE FIELD and it is not written either. It names the ROOT
#    type of the resource file. Measured (core.ypt + cut_arena.ypt, same values):
#      PtfxList.FileVFT          = 1080047976
#      TextureDictionary.FileVFT = 1079481784
#    When the FileVFT of the EMBEDDED texture dictionary stays zero the engine does
#    not recognise the dictionary: the texture binds and draws, but SHEET SLICING
#    does not work. Measured case: the same vanilla texture is sliced when it is
#    referenced from core.ypt, but not when it is embedded in our file.
$FILEVFT_PTFXLIST = 1080047976
$FILEVFT_TEXDICT  = 1079481784

$pl = $ypt.PtfxList
if ([uint32]$pl.FileVFT -ne $FILEVFT_PTFXLIST) {
    $pl.FileVFT = [uint32]$FILEVFT_PTFXLIST; $vftN++
}
if ($pl.TextureDictionary -and [uint32]$pl.TextureDictionary.FileVFT -ne $FILEVFT_TEXDICT) {
    $pl.TextureDictionary.FileVFT = [uint32]$FILEVFT_TEXDICT; $vftN++
}
Vft $pl.EffectRuleDictionary   $VFT_BLOCK.EffectRuleDict
Vft $pl.EmitterRuleDictionary  $VFT_BLOCK.EmitterRuleDict
Vft $pl.ParticleRuleDictionary $VFT_BLOCK.ParticleRuleDict

if ($pl.TextureDictionary -and $pl.TextureDictionary.Textures) {
    foreach ($t in $pl.TextureDictionary.Textures.data_items) { Vft $t $VFT_BLOCK.Texture }
}
foreach ($er in $pl.EffectRuleDictionary.EffectRules.data_items) {
    Vft $er $VFT_BLOCK.EffectRule
    if ($er.EventEmitters -and $er.EventEmitters.data_items) {
        foreach ($ee in $er.EventEmitters.data_items) {
            if ($ee.EmitterRuleName) { Vft $ee $VFT_BLOCK.EventEmitter }
        }
    }
    foreach ($n in 0..4) { Vft $er."KeyframeProp$n" $VFT_BLOCK.KeyframeProp }
}
foreach ($em in $pl.EmitterRuleDictionary.EmitterRules.data_items) {
    Vft $em $VFT_BLOCK.EmitterRule
    foreach ($kp in $em.KeyframeProps1) { Vft $kp $VFT_BLOCK.KeyframeProp }
    foreach ($dn in 'Domain1', 'Domain2', 'Domain3') {
        $dm = $em.$dn
        if ($dm) {
            Vft $dm $VFT_DOMAIN[[string]$dm.DomainType]
            foreach ($n in 0..3) { Vft $dm."KeyframeProp$n" $VFT_BLOCK.KeyframeProp }
        }
    }
}
foreach ($pr in $pl.ParticleRuleDictionary.ParticleRules.data_items) {
    Vft $pr $VFT_BLOCK.ParticleRule
    if ($pr.ShaderVars -and $pr.ShaderVars.data_items) {
        foreach ($sv in $pr.ShaderVars.data_items) {
            Vft $sv $VFT_SHADERVAR[[string]$sv.Type]
        }
    }
    foreach ($ln in 'BehaviourList1', 'BehaviourList2', 'BehaviourList3', 'BehaviourList5') {
        $bl = $pr.$ln
        if (-not $bl -or -not $bl.data_items) { continue }
        foreach ($b in $bl.data_items) {
            Vft $b $VFT_BEHAVIOUR[[string]$b.Type]
            foreach ($n in 0..3) { Vft $b."KeyframeProp$n" $VFT_BLOCK.KeyframeProp }
        }
    }
}
Write-Host ("[+] VFT written: {0} blocks" -f $vftN)

# --- 2) write by hand the hash CodeWalker does not write ---
$hashFixed = 0
foreach ($pr in $ypt.PtfxList.ParticleRuleDictionary.ParticleRules.data_items) {
    $fxcName = [string]$pr.FxcFile
    if (-not $fxcName) { throw "FxcFile is empty for particle rule '$($pr.Name)'" }
    $h = [CodeWalker.GameFiles.JenkHash]::GenHash($fxcName)
    if ([uint32]$pr.FxcFileHash -ne $h) {
        $pr.FxcFileHash = $h
        $hashFixed++
    }
}
Write-Host ("[+] FxcFileHash written: {0} particle rules" -f $hashFixed)

# --- 3) Save ---
$bytes = $ypt.Save()
[IO.File]::WriteAllBytes($Out, $bytes)
Write-Host ("[+] {0}  {1:N0} bytes" -f $Out, $bytes.Length)

# --- 4) VERIFY BY READING BACK -- the file size is NOT a validity measure ---
$d = [IO.File]::ReadAllBytes($Out)
$e = [CodeWalker.GameFiles.RpfFile]::CreateResourceFileEntry([ref]$d, 0)
$d = [CodeWalker.GameFiles.ResourceBuilder]::Decompress($d)
$y2 = New-Object CodeWalker.GameFiles.YptFile
$y2.Load($d, $e)
$p = $y2.PtfxList

$failures = @()
if (-not $p.EffectRuleDictionary.EffectRules.data_items.Count) { $failures += "EffectRules empty" }
if ([uint32]$p.FileVFT -eq 0) { $failures += "PtfxList.FileVFT ZERO" }
if ($p.TextureDictionary -and $p.TextureDictionary.Textures) {
    if ([uint32]$p.TextureDictionary.FileVFT -eq 0) {
        $failures += "TextureDictionary.FileVFT ZERO (the embedded texture will not slice)"
    }
    foreach ($t in $p.TextureDictionary.Textures.data_items) {
        if ([uint32]$t.VFT -eq 0) { $failures += "texture VFT ZERO: $($t.Name)" }
    }
}
foreach ($pr in $p.ParticleRuleDictionary.ParticleRules.data_items) {
    if ([uint32]$pr.VFT -eq 0) { $failures += "particle rule VFT ZERO: $($pr.Name)" }
    if ($pr.ShaderVars -and $pr.ShaderVars.data_items) {
        foreach ($sv in $pr.ShaderVars.data_items) {
            if ([uint32]$sv.VFT -eq 0) {
                $failures += "ShaderVar VFT ZERO: $($pr.Name)/$($sv.Name)"
            }
        }
    }
    if ([uint32]$pr.FxcFileHash -eq 0) { $failures += "FxcFileHash ZERO: $($pr.Name)" }
    $bl = $pr.BehaviourList1
    if (-not $bl -or -not $bl.data_items -or $bl.data_items.Count -eq 0) {
        $failures += "no behaviours: $($pr.Name)"
    }
}

Write-Host "--- read back ---"
Write-Host ("    Name          : {0}" -f $p.Name)
Write-Host ("    EffectRules   : {0}" -f (($p.EffectRuleDictionary.EffectRules.data_items | ForEach-Object { $_.Name }) -join ', '))
foreach ($pr in $p.ParticleRuleDictionary.ParticleRules.data_items) {
    Write-Host ("    {0,-16}: shader={1} hash={2} behaviours={3}" -f `
        $pr.Name, $pr.FxcFile, [uint32]$pr.FxcFileHash, $pr.BehaviourList1.data_items.Count)
}
if ($p.TextureDictionary -and $p.TextureDictionary.Textures) {
    foreach ($t in $p.TextureDictionary.Textures.data_items) {
        Write-Host ("    texture       : {0} {1}x{2} {3}" -f $t.Name, $t.Width, $t.Height, $t.Format)
    }
}

if ($failures.Count) {
    Write-Host "[!] VERIFICATION FAILED:" -ForegroundColor Red
    $failures | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
    exit 1
}
Write-Host "[=] verification passed."

# --- 5) DEPLOY ---
# !! -LiteralPath IS REQUIRED. FiveM resource paths contain folders with square
#    brackets such as `[script]`; PowerShell takes them for a WILDCARD and
#    Copy-Item SILENTLY does nothing. This really happened:
#    the file was compiled, "copied" was printed, stream/ stayed on the old version
#    and the old effect was tested in the game for hours.
#    That is why the SIZE IS COMPARED after the copy.
if ($Deploy) {
    if (-not (Test-Path -LiteralPath $Deploy)) {
        # New-Item has no -LiteralPath (PowerShell 5.1 throws); its -Path takes brackets literally (tested with [script]).
        New-Item -ItemType Directory -Force -Path $Deploy | Out-Null
    }
    $destPath = Join-Path $Deploy (Split-Path $Out -Leaf)
    Copy-Item -LiteralPath $Out -Destination $destPath -Force
    $srcSize = (Get-Item -LiteralPath $Out).Length
    $dstSize = (Get-Item -LiteralPath $destPath).Length
    if ($srcSize -ne $dstSize) {
        Write-Host "[!] DEPLOY COULD NOT BE VERIFIED: source $srcSize bytes, target $dstSize bytes" -ForegroundColor Red
        exit 1
    }
    Write-Host ("[=] deployed -> {0}  ({1:N0} bytes, verified)" -f $destPath, $dstSize)
}
