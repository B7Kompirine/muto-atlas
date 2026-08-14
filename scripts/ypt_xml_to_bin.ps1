# ypt_xml_to_bin.ps1 — .ypt.xml -> ikili .ypt (CodeWalker hatasi yamanmis).
#
# ⛔ NEDEN AYRI BETIK: CodeWalker'in XML okuyucusu `FxcFileHash` alanini
#    HIC YAZMAZ. Olculdu -- bozulmamis bir vanilla dosyayla:
#
#      cut_arena.ypt  ikili okuma   -> FxcFileHash = 246470498
#      ayni dosya     XML turundan  -> FxcFileHash = 0
#
#    Yani sorun bizim XML'imizde degil, aracin kendisinde; XML'den uretilen
#    HER .ypt shader'siz cikar. `FxcFile` metni dogru gorunur, hash sifirdir
#    ve motorun baktigi sey hash'tir. Belirti: dosya gecerli, `.ypt` yuklenir,
#    StartParticleFx* SIFIRDAN FARKLI handle dondurur ve EKRANDA HICBIR SEY
#    OLMAZ. Bu belirtiyi baska hicbir denetim yakalamaz.
#
#    Duzeltme JenkHash: GenHash('ptfx_sprite') = 246470498, vanilla ikili
#    degerle birebir. `FxcTechniqueHash` vanilla'da da 0 -- ona dokunma.
#
# Kullanim:
#   powershell -File ypt_xml_to_bin.ps1 -Xml <yol\ad.ypt.xml> [-Out <yol\ad.ypt>]
#   (DDS dosyalari XML ile AYNI KLASORDE olmali.)

param(
    [Parameter(Mandatory = $true)][string] $Xml,
    [string] $Out,
    [string] $Deploy,          # hedef stream/ klasoru (opsiyonel)
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

if (-not $CodeWalker) {
    $CodeWalker = @(
        "$env:USERPROFILE\Desktop\FiveM\CodeWalker30_dev46\CodeWalker.Core.dll",
        "$env:USERPROFILE\Desktop\CodeWalker\CodeWalker.Core.dll"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $CodeWalker) { throw "CodeWalker.Core.dll bulunamadi" }
[Reflection.Assembly]::LoadFrom($CodeWalker) | Out-Null

if (-not (Test-Path -LiteralPath $Xml)) { throw "XML yok: $Xml" }
$klasor = Split-Path -Parent (Resolve-Path -LiteralPath $Xml)
if (-not $Out) { $Out = ($Xml -replace '\.ypt\.xml$', '.ypt') }

# --- 1) XML -> nesne agaci ---
$doc = New-Object System.Xml.XmlDocument
$doc.Load((Resolve-Path -LiteralPath $Xml))
$ypt = [CodeWalker.GameFiles.XmlYpt]::GetYpt($doc, $klasor)

# --- 1b) VFT: CodeWalker XML okuyucusu HICBIR bloga VFT yazmaz ---
#
# ⛔ VFT = nesnenin sinif kimligi (vtable). Sifir birakilirsa motor blogun
#    TURUNU cozemez. Belirti sinsi: efekt yuklenir, parcacik cizilir, ama
#    sinifa ozgu davranis calismaz. Olculen vaka: sprite sheet dokusu
#    DILIMLENMEZ -- 2x2 sheet'in dordu birden tek quad'a cizilir. Ayni
#    kural vanilla dokusuyla dogru dilimliyordu; tek fark VFT'ydi.
#
# Degerler core.ypt'ten olculdu ve HER TIP TEK DEGER tasiyor, sifir sapma:
#   Textures 107/107 · EffectRules 964/964 · EmitterRules 1993/1993
#   ParticleRules 1736/1736 · EventEmitter 2543/2543 · KeyframeProp 4820/4820
#   davranislar tip basina 1 deger · domain'ler sekil basina 1 deger
$VFT_BLOK = @{
    EffectRuleDict   = 1080048016; EmitterRuleDict = 1080048056
    ParticleRuleDict = 1080048096; Texture         = 1080137320
    EffectRule       = 1080081688; EmitterRule     = 1080083608
    ParticleRule     = 1080085192; EventEmitter    = 1080100952
    KeyframeProp     = 1080085392
}
$VFT_DAVRANIS = @{
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
# ⛔ ShaderVars girdilerinin de kendi VFT'si var -- ve DOKU BAGINI KURAN
#    nesne budur (Type=Texture). Sifir kalinca doku baglanip cizilir ama
#    sheet dilimlemesi calismaz. Olculdu: Texture 5108/5108, Vector2
#    18846/18846, Keyframe 10216/10216 -- her tip tek deger.
#    Vector4 ile Vector2 AYNI VFT'yi paylasiyor (1080097368).
$VFT_SHADERVAR = @{
    Texture = 1080097544; Vector2 = 1080097368
    Vector4 = 1080097368; Keyframe = 1080097256
}

$vftN = 0
function Vft($o, $deger) {
    if ($null -eq $o -or $null -eq $deger) { return }
    if ([uint32]$o.VFT -ne [uint32]$deger) { $o.VFT = [uint32]$deger; $script:vftN++ }
}

# ⛔ `FileVFT` AYRI BIR ALAN ve o da yazilmiyor. Kaynak dosyanin KOK
#    tipini belirtir. Olculdu (core.ypt + cut_arena.ypt, ayni degerler):
#      PtfxList.FileVFT          = 1080047976
#      TextureDictionary.FileVFT = 1079481784
#    GOMULU doku sozlugunun FileVFT'si sifir kalinca motor sozlugu
#    taniyamiyor: doku baglaniyor ve ciziliyor, ama SHEET DILIMLEMESI
#    calismiyor. Olculen vaka: ayni vanilla doku core.ypt'ten
#    referansla dilimleniyor, bizim dosyaya gomulunce dilimlenmiyor.
$FILEVFT_PTFXLIST = 1080047976
$FILEVFT_TEXDICT  = 1079481784

$pl = $ypt.PtfxList
if ([uint32]$pl.FileVFT -ne $FILEVFT_PTFXLIST) {
    $pl.FileVFT = [uint32]$FILEVFT_PTFXLIST; $vftN++
}
if ($pl.TextureDictionary -and [uint32]$pl.TextureDictionary.FileVFT -ne $FILEVFT_TEXDICT) {
    $pl.TextureDictionary.FileVFT = [uint32]$FILEVFT_TEXDICT; $vftN++
}
Vft $pl.EffectRuleDictionary   $VFT_BLOK.EffectRuleDict
Vft $pl.EmitterRuleDictionary  $VFT_BLOK.EmitterRuleDict
Vft $pl.ParticleRuleDictionary $VFT_BLOK.ParticleRuleDict

if ($pl.TextureDictionary -and $pl.TextureDictionary.Textures) {
    foreach ($t in $pl.TextureDictionary.Textures.data_items) { Vft $t $VFT_BLOK.Texture }
}
foreach ($er in $pl.EffectRuleDictionary.EffectRules.data_items) {
    Vft $er $VFT_BLOK.EffectRule
    if ($er.EventEmitters -and $er.EventEmitters.data_items) {
        foreach ($ee in $er.EventEmitters.data_items) {
            if ($ee.EmitterRuleName) { Vft $ee $VFT_BLOK.EventEmitter }
        }
    }
    foreach ($n in 0..4) { Vft $er."KeyframeProp$n" $VFT_BLOK.KeyframeProp }
}
foreach ($em in $pl.EmitterRuleDictionary.EmitterRules.data_items) {
    Vft $em $VFT_BLOK.EmitterRule
    foreach ($kp in $em.KeyframeProps1) { Vft $kp $VFT_BLOK.KeyframeProp }
    foreach ($dn in 'Domain1', 'Domain2', 'Domain3') {
        $dm = $em.$dn
        if ($dm) {
            Vft $dm $VFT_DOMAIN[[string]$dm.DomainType]
            foreach ($n in 0..3) { Vft $dm."KeyframeProp$n" $VFT_BLOK.KeyframeProp }
        }
    }
}
foreach ($pr in $pl.ParticleRuleDictionary.ParticleRules.data_items) {
    Vft $pr $VFT_BLOK.ParticleRule
    if ($pr.ShaderVars -and $pr.ShaderVars.data_items) {
        foreach ($sv in $pr.ShaderVars.data_items) {
            Vft $sv $VFT_SHADERVAR[[string]$sv.Type]
        }
    }
    foreach ($ln in 'BehaviourList1', 'BehaviourList2', 'BehaviourList3', 'BehaviourList5') {
        $bl = $pr.$ln
        if (-not $bl -or -not $bl.data_items) { continue }
        foreach ($b in $bl.data_items) {
            Vft $b $VFT_DAVRANIS[[string]$b.Type]
            foreach ($n in 0..3) { Vft $b."KeyframeProp$n" $VFT_BLOK.KeyframeProp }
        }
    }
}
Write-Host ("[+] VFT yazildi: {0} blok" -f $vftN)

# --- 2) CodeWalker'in yazmadigi hash'i elle yaz ---
$duzeltilen = 0
foreach ($pr in $ypt.PtfxList.ParticleRuleDictionary.ParticleRules.data_items) {
    $ad = [string]$pr.FxcFile
    if (-not $ad) { throw "particle rule '$($pr.Name)' icin FxcFile bos" }
    $h = [CodeWalker.GameFiles.JenkHash]::GenHash($ad)
    if ([uint32]$pr.FxcFileHash -ne $h) {
        $pr.FxcFileHash = $h
        $duzeltilen++
    }
}
Write-Host ("[+] FxcFileHash yazildi: {0} particle rule" -f $duzeltilen)

# --- 3) Kaydet ---
$bayt = $ypt.Save()
[IO.File]::WriteAllBytes($Out, $bayt)
Write-Host ("[+] {0}  {1:N0} bayt" -f $Out, $bayt.Length)

# --- 4) GERI OKUYARAK DOGRULA -- boyut gecerlilik olcutu DEGILDIR ---
$d = [IO.File]::ReadAllBytes($Out)
$e = [CodeWalker.GameFiles.RpfFile]::CreateResourceFileEntry([ref]$d, 0)
$d = [CodeWalker.GameFiles.ResourceBuilder]::Decompress($d)
$y2 = New-Object CodeWalker.GameFiles.YptFile
$y2.Load($d, $e)
$p = $y2.PtfxList

$hata = @()
if (-not $p.EffectRuleDictionary.EffectRules.data_items.Count) { $hata += "EffectRules bos" }
if ([uint32]$p.FileVFT -eq 0) { $hata += "PtfxList.FileVFT SIFIR" }
if ($p.TextureDictionary -and $p.TextureDictionary.Textures) {
    if ([uint32]$p.TextureDictionary.FileVFT -eq 0) {
        $hata += "TextureDictionary.FileVFT SIFIR (gomulu doku dilimlenmez)"
    }
    foreach ($t in $p.TextureDictionary.Textures.data_items) {
        if ([uint32]$t.VFT -eq 0) { $hata += "doku VFT SIFIR: $($t.Name)" }
    }
}
foreach ($pr in $p.ParticleRuleDictionary.ParticleRules.data_items) {
    if ([uint32]$pr.VFT -eq 0) { $hata += "particle rule VFT SIFIR: $($pr.Name)" }
    if ($pr.ShaderVars -and $pr.ShaderVars.data_items) {
        foreach ($sv in $pr.ShaderVars.data_items) {
            if ([uint32]$sv.VFT -eq 0) {
                $hata += "ShaderVar VFT SIFIR: $($pr.Name)/$($sv.Name)"
            }
        }
    }
    if ([uint32]$pr.FxcFileHash -eq 0) { $hata += "FxcFileHash SIFIR: $($pr.Name)" }
    $bl = $pr.BehaviourList1
    if (-not $bl -or -not $bl.data_items -or $bl.data_items.Count -eq 0) {
        $hata += "davranis yok: $($pr.Name)"
    }
}

Write-Host "--- geri okuma ---"
Write-Host ("    Name          : {0}" -f $p.Name)
Write-Host ("    EffectRules   : {0}" -f (($p.EffectRuleDictionary.EffectRules.data_items | ForEach-Object { $_.Name }) -join ', '))
foreach ($pr in $p.ParticleRuleDictionary.ParticleRules.data_items) {
    Write-Host ("    {0,-16}: shader={1} hash={2} davranis={3}" -f `
        $pr.Name, $pr.FxcFile, [uint32]$pr.FxcFileHash, $pr.BehaviourList1.data_items.Count)
}
if ($p.TextureDictionary -and $p.TextureDictionary.Textures) {
    foreach ($t in $p.TextureDictionary.Textures.data_items) {
        Write-Host ("    doku          : {0} {1}x{2} {3}" -f $t.Name, $t.Width, $t.Height, $t.Format)
    }
}

if ($hata.Count) {
    Write-Host "[!] DOGRULAMA BASARISIZ:" -ForegroundColor Red
    $hata | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
    exit 1
}
Write-Host "[=] dogrulama gecti."

# --- 5) DAGITIM ---
# ⛔ -LiteralPath ZORUNLU. FiveM kaynak yollari `[script]` gibi kose
#    parantezli klasorler icerir; PowerShell bunu JOKER sanar ve
#    Copy-Item SESSIZCE hicbir sey yapmaz. Bu tam olarak yasandi:
#    dosya derlendi, "kopyalandi" yazildi, stream/ eski surumde kaldi
#    ve oyunda saatlerce eski efekt test edildi.
#    Bu yuzden kopyadan sonra BOYUT KARSILASTIRILIYOR.
if ($Deploy) {
    if (-not (Test-Path -LiteralPath $Deploy)) {
        New-Item -ItemType Directory -Force -LiteralPath $Deploy | Out-Null
    }
    $hedef = Join-Path $Deploy (Split-Path $Out -Leaf)
    Copy-Item -LiteralPath $Out -Destination $hedef -Force
    $k = (Get-Item -LiteralPath $Out).Length
    $h = (Get-Item -LiteralPath $hedef).Length
    if ($k -ne $h) {
        Write-Host "[!] DAGITIM DOGRULANAMADI: kaynak $k bayt, hedef $h bayt" -ForegroundColor Red
        exit 1
    }
    Write-Host ("[=] dagitildi -> {0}  ({1:N0} bayt, dogrulandi)" -f $hedef, $h)
}
