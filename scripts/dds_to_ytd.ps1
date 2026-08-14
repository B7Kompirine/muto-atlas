# dds_to_ytd.ps1 -- klasordeki .dds dosyalarindan .ytd doku sozlugu uretir.
#
# NEDEN: Sollumz .ytd URETEMEZ (sollum_type listesinde texture dictionary yok)
#        ve Blender DDS YAZAMAZ. Bu iki bosluktan ikincisi bake_to_gta.py ile,
#        birincisi bu betikle kapanir.
#
# !! Cikis boyutu gecerlilik olcutu DEGILDIR -- RSC7 zlib sikistirilmistir.
#    Bu yuzden betik uretimden sonra dosyayi GERI OKUR ve doku sayisi/adi/
#    formatini dogrular. Dogrulama gecmezse exit 1.
#
# Kullanim:
#   pwsh dds_to_ytd.ps1 -Girdi out\ -Cikti stream\mtk_kaldirim.ytd
#   pwsh dds_to_ytd.ps1 -Girdi out\ -Cikti x.ytd -CodeWalker C:\...\CodeWalker.Core.dll

[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $Girdi,
    [Parameter(Mandatory)][string] $Cikti,
    # Shader'in KULLANMADIGI dokuyu sozluge koyma. Ornek: cutout_fence_normal'da
    # SpecSampler yoktur, '*_s.dds' bosuna ~175 KB stream yuku olur.
    [string[]] $Haric = @(),
    [string] $CodeWalker = 'C:\Users\musti\Desktop\FiveM\CodeWalker30_dev46\CodeWalker.Core.dll'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $CodeWalker)) { throw "CodeWalker.Core.dll yok: $CodeWalker" }
if (-not (Test-Path -LiteralPath $Girdi))      { throw "girdi klasoru yok: $Girdi" }
Add-Type -Path $CodeWalker

$tum = @(Get-ChildItem -LiteralPath $Girdi -Filter *.dds -File | Sort-Object Name)
$ddsler = @($tum | Where-Object { $ad = $_.Name; -not ($Haric | Where-Object { $ad -like $_ }) })
foreach ($a in ($tum | Where-Object { $ddsler -notcontains $_ })) {
    "  - {0,-28} HARIC TUTULDU" -f $a.Name
}
if ($ddsler.Count -eq 0) { throw "$Girdi icinde (filtreden sonra) .dds yok" }

$liste = New-Object "System.Collections.Generic.List[CodeWalker.GameFiles.Texture]"
foreach ($f in $ddsler) {
    $bayt = [System.IO.File]::ReadAllBytes($f.FullName)
    $tex  = [CodeWalker.Utils.DDSIO]::GetTexture($bayt)
    if (-not $tex) { throw "DDS okunamadi: $($f.Name)" }
    $tex.Name = $f.BaseName
    # !! Ad hash'i motorun dokuyu buldugu anahtardir; adi elle yazip hash'i
    #    bos birakmak dokuyu bulunamaz yapar.
    $tex.NameHash = [CodeWalker.GameFiles.JenkHash]::GenHash($f.BaseName.ToLower())
    $liste.Add($tex)
    "  + {0,-28} {1}x{2} {3} mip={4}" -f $tex.Name, $tex.Width, $tex.Height, $tex.Format, $tex.Levels
}

$td = New-Object CodeWalker.GameFiles.TextureDictionary
$td.BuildFromTextureList($liste)
$ytd = New-Object CodeWalker.GameFiles.YtdFile
$ytd.TextureDict = $td
$veri = $ytd.Save()

$dizin = Split-Path -Parent $Cikti
if ($dizin -and -not (Test-Path -LiteralPath $dizin)) {
    New-Item -ItemType Directory -Force -Path $dizin | Out-Null
}
[System.IO.File]::WriteAllBytes($Cikti, $veri)
"`n[yazildi] $Cikti  ($('{0:N0}' -f $veri.Length) bayt, zlib sikistirilmis)"

# ---- GERI OKUMA: tek gecerli olcut ------------------------------------
$ham   = [System.IO.File]::ReadAllBytes($Cikti)
$entry = [CodeWalker.GameFiles.RpfFile]::CreateResourceFileEntry([ref]$ham, 0)
$acik  = [CodeWalker.GameFiles.ResourceBuilder]::Decompress($ham)
$geri  = New-Object CodeWalker.GameFiles.YtdFile
$geri.Load($acik, $entry)

$okunan = @($geri.TextureDict.Textures.data_items | Where-Object { $_ })
"`n=== GERI OKUMA ==="
"  doku sayisi: $($okunan.Count) (beklenen $($liste.Count))"
$hata = 0
if ($okunan.Count -ne $liste.Count) { $hata++ }
foreach ($t in $okunan) {
    $kaynak = $liste | Where-Object { $_.Name -eq $t.Name } | Select-Object -First 1
    if (-not $kaynak) { "  HATA: beklenmeyen doku '$($t.Name)'"; $hata++; continue }
    $ok = ($t.Width -eq $kaynak.Width) -and ($t.Height -eq $kaynak.Height) -and
          ($t.Format -eq $kaynak.Format) -and ($t.Levels -eq $kaynak.Levels)
    if (-not $ok) { $hata++ }
    "  {0,-28} {1}x{2} {3} mip={4}  {5}" -f $t.Name, $t.Width, $t.Height, $t.Format,
        $t.Levels, $(if ($ok) { 'OK' } else { 'HATA' })
    if ($t.NameHash -eq 0) { "    HATA: NameHash 0 -- motor bu dokuyu bulamaz"; $hata++ }
}

if ($hata -gt 0) { "`n$hata DOGRULAMA HATASI"; exit 1 }
"`nTUM DENETIMLER GECTI"
exit 0
