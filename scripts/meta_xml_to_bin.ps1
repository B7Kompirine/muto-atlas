# meta_xml_to_bin.ps1 - .ytyp.xml / .ymap.xml -> oyuna hazir binary.
#
# NEDEN AYRI BIR ARAC: muto-atlas'taki xml_to_res.ps1 yalniz kaynak (RSC)
# tiplerini tanir (.yft .ydd .ydr .ybn .ypt .ytd ...); .ytyp ve .ymap orada
# YOK. Ikisi de MetaFormat.RSC uzerinden XmlMeta.GetData ile yazilir.
#
# OLCULDU: des_protree.ytyp icin XML -> binary -> XML turu 4.978 baytin
# tamaminda BIREBIR ayni cikti (compositeEntityTypes / Animations /
# effectsData dahil). Yani tur kayipsiz.
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File meta_xml_to_bin.ps1 -XmlPath x.ytyp.xml
#   ... -XmlPath x.ymap.xml -OutPath baska\yer\x.ymap

param(
    [Parameter(Mandatory=$true)][string] $XmlPath,
    [string] $OutPath,
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

# Yol icinde [script] gibi kose parantez varsa Test-Path onu joker sanar.
if (-not (Test-Path -LiteralPath $XmlPath)) { throw "XML bulunamadi: $XmlPath" }
if (-not $OutPath) { $OutPath = $XmlPath -replace '\.xml$', '' }

if (-not $CodeWalker) {
    $CodeWalker = @(
        "$env:USERPROFILE\Desktop\FiveM\CodeWalker30_dev46\CodeWalker.Core.dll",
        "$env:USERPROFILE\Desktop\CodeWalker\CodeWalker.Core.dll"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $CodeWalker) { throw "CodeWalker.Core.dll bulunamadi." }

Add-Type -Path $CodeWalker
$asm = [System.Reflection.Assembly]::LoadFrom($CodeWalker)
$mf  = $asm.GetType('CodeWalker.GameFiles.MetaFormat')

$ext = [System.IO.Path]::GetExtension($OutPath).ToLowerInvariant()
if ($ext -ne '.ytyp' -and $ext -ne '.ymap' -and $ext -ne '.ymt') {
    throw "Desteklenmeyen uzanti '$ext'. Bu arac yalniz .ytyp / .ymap / .ymt yazar."
}

$doc = New-Object System.Xml.XmlDocument
$doc.Load((Resolve-Path -LiteralPath $XmlPath))

$folder = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($XmlPath))
$data = [CodeWalker.GameFiles.XmlMeta]::GetData($doc, [Enum]::Parse($mf, 'RSC'), $folder)
if (-not $data) { throw "XmlMeta.GetData null dondu -- XML yapisi bozuk olabilir." }

[System.IO.File]::WriteAllBytes($OutPath, $data)

# GERI OKU. Boyut gecerlilik olcutu DEGILDIR (RSC7 zlib sikistirilmis);
# tek gecerli olcut geri okumadir.
if ($ext -eq '.ymt') {
    # CPedVariationInfo vb. RSC meta. Geri oku, kok blok adini yaz.
    $y = New-Object CodeWalker.GameFiles.YmtFile
    $y.Load([System.IO.File]::ReadAllBytes($OutPath))
    $root = if ($y.Meta -and $y.Meta.DataBlocks) { $y.Meta.DataBlocks.Count } else { 0 }
    Write-Host ("[+] {0}  {1} bayt  -> meta blok={2}" -f [System.IO.Path]::GetFileName($OutPath), $data.Length, $root)
    if ($root -eq 0) { Write-Host "[!] meta blok 0 -- dosya bos yazildi."; exit 1 }
} elseif ($ext -eq '.ytyp') {
    $y = New-Object CodeWalker.GameFiles.YtypFile
    $y.Load([System.IO.File]::ReadAllBytes($OutPath))
    $na = if ($y.AllArchetypes) { $y.AllArchetypes.Count } else { 0 }
    $nc = if ($y.CompositeEntityTypes) { $y.CompositeEntityTypes.Count } else { 0 }
    Write-Host ("[+] {0}  {1} bayt  -> archetype={2}  compositeEntityTypes={3}" -f `
        [System.IO.Path]::GetFileName($OutPath), $data.Length, $na, $nc)
    if ($na -eq 0) { Write-Host "[!] archetype 0 -- dosya bos yazildi."; exit 1 }
} else {
    $d = [System.IO.File]::ReadAllBytes($OutPath)
    $e = [CodeWalker.GameFiles.RpfFile]::CreateResourceFileEntry([ref]$d, 0)
    $d = [CodeWalker.GameFiles.ResourceBuilder]::Decompress($d)
    $y = New-Object CodeWalker.GameFiles.YmapFile
    $y.Load($d, $e)
    $ents = $y.AllEntities; if (-not $ents) { $ents = $y.RootEntities }
    $n = if ($ents) { $ents.Count } else { 0 }

    # ⛔ KAYIP KAPISI. XmlMeta.GetData BAZI ymap'lerde entity DUSURUYOR ve
    # sessizce basarili donuyor. Olculdu: hw1_rd_critical_1.ymap dosyaya HIC
    # DOKUNMADAN yapilan turda bile 457 -> 128. Dagitilsaydi o bolgedeki 325
    # obje (agac, tabela, trafik isigi, cop kutusu) sessizce yok olacakti.
    # Bu yuzden XML'deki Item sayisiyla karsilastirmadan dosya birakilmaz.
    $xmlSay = $doc.SelectNodes('//entities/Item').Count
    Write-Host ("[+] {0}  {1} bayt  -> entity={2} (XML {3})  parent={4}" -f `
        [System.IO.Path]::GetFileName($OutPath), $data.Length, $n, $xmlSay, $y.CMapData.parent)
    if ($n -eq 0) { Write-Host "[!] entity 0 -- dosya bos yazildi."; exit 1 }
    if ($xmlSay -gt 0 -and $n -ne $xmlSay) {
        Write-Host ("[!] KAYIP: XML {0} entity, binary {1}. Bu dosya XML turunu KAYIPSIZ" -f $xmlSay, $n)
        Write-Host    "    GECMIYOR -- dagitma. Yerine YmapFile.RemoveEntity + YmapFile.Save()"
        Write-Host    "    kullan (ayni dosyada kayipsiz olculdu)."
        Remove-Item -LiteralPath $OutPath -Force
        exit 1
    }
}
