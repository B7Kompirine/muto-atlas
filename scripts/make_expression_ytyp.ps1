# make_expression_ytyp.ps1 — Expression extension'LI ytyp uretir.
#
# NEDEN AYRI SCRIPT: make_ytyp_override.ps1 nesne modeliyle calisiyor ve
# Archetype.Extensions'a yazmak SERILESMIYOR — ytyp geri okundugunda
# Extensions bos cikiyor. (Sebep: CBaseArchetypeDef.extensions ham
# Array_StructurePointer; Save() onu nesne modelinden doldurmuyor.)
#
# TUTAN YOL: ytyp'yi XML'den uretmek.
#   [CodeWalker.GameFiles.XmlMeta]::GetData($doc, [MetaFormat]::RSC, "")
# DIKKAT: MetaFormat'ta 'ytyp' YOK — ytyp bir RSC meta'dir, RSC kullanilir.
#
# DOGRULAMA (bunu gormeden "oldu" deme):
#   ext: MCExtensionDefExpression  dict=<ad>  name=<ad>
#
# Asagidaki XML sablonunda model adini/olculeri degistirerek kullan.
# expressionDictionaryName / expressionName CIPLAK ad olmali —
# "pack:/x.expr" yazarsan expression hic yuklenmez ama mesh animasyonu
# calismaya devam eder, hatayi fark etmek cok zor olur.

param(
  # Cikti .ytyp yolu. GOMULU VARSAYILAN YOK: kisisel bir sunucu yolunu
  # varsayilan yapmak baskasinin makinesinde sessizce yanlis yere yazar.
  [Parameter(Mandatory=$true)][string] $OutPath
)

$ErrorActionPreference='Stop'
$cw = & "$PSScriptRoot\yol.ps1" codewalker
if (-not $cw) { throw "CodeWalker.Core.dll bulunamadi. python assetdb.py yol codewalker ""<yol>""" }
$script:cwDir = Split-Path $cw -Parent
[System.AppDomain]::CurrentDomain.add_AssemblyResolve([System.ResolveEventHandler]{
  param($s,$e); $n=($e.Name -split ',')[0]; $p=Join-Path $script:cwDir "$n.dll"
  if (Test-Path -LiteralPath $p) { return [System.Reflection.Assembly]::LoadFrom($p) }; return $null })
[void][System.Reflection.Assembly]::LoadFrom($cw)

$xml = @'
<?xml version="1.0" encoding="UTF-8"?>
<CMapTypes>
  <extensions/>
  <archetypes>
    <Item type="CBaseArchetypeDef">
      <lodDist value="200"/>
      <flags value="537526784"/>
      <specialAttribute value="0"/>
      <bbMin x="-0.104407" y="-0.106897" z="-1.161611"/>
      <bbMax x="1.623763" y="0.263908" z="1.161063"/>
      <bsCentre x="0.759678" y="0.078506" z="-0.000274"/>
      <bsRadius value="1.4594"/>
      <hdTextureDist value="100"/>
      <name>muto_vauldr</name>
      <textureDictionary/>
      <clipDictionary>muto_vauldr_anim</clipDictionary>
      <drawableDictionary/>
      <physicsDictionary>muto_vauldr</physicsDictionary>
      <assetType>ASSET_TYPE_FRAGMENT</assetType>
      <assetName>muto_vauldr</assetName>
      <extensions>
        <Item type="CExtensionDefExpression">
          <name>muto_vauldr</name>
          <offsetPosition x="0" y="0" z="0"/>
          <expressionDictionaryName>muto_vauldr</expressionDictionaryName>
          <expressionName>muto_vauldr</expressionName>
          <creatureMetadataName/>
          <initialiseOnCollision value="false"/>
        </Item>
      </extensions>
    </Item>
  </archetypes>
  <name>muto_vauldr</name>
  <dependencies/>
  <compositeEntityTypes/>
</CMapTypes>
'@

$doc = New-Object System.Xml.XmlDocument
$doc.LoadXml($xml)

$fmt = [CodeWalker.GameFiles.MetaFormat]::RSC
$data = [CodeWalker.GameFiles.XmlMeta]::GetData($doc, $fmt, "")
if (-not $data) { Write-Host "[X] GetData null dondu"; exit 1 }

# Cikti yolu ZORUNLU parametredir; gomulu bir sunucu yolu baskasinda anlamsizdir.
if (-not $OutPath) { throw "OutPath gerekli: -OutPath <...\stream\<ad>.ytyp>" }
$out = $OutPath
[System.IO.File]::WriteAllBytes($out, $data)
Write-Host ("[+] yazildi: {0} bayt" -f $data.Length)

# DOGRULA
$y = New-Object CodeWalker.GameFiles.YtypFile
$y.Load([System.IO.File]::ReadAllBytes($out))
foreach ($a in $y.AllArchetypes) {
  $d = $a._BaseArchetypeDef
  Write-Host ("name={0} assetType={1} clipDict={2} physDict={3} flags={4}" -f $d.name,$d.assetType,$d.clipDictionary,$d.physicsDictionary,$d.flags)
  if ($a.Extensions) {
    foreach ($e in $a.Extensions) {
      Write-Host ("  ext: {0}  dict={1}  name={2}" -f $e.GetType().Name, $e._Data.expressionDictionaryName, $e._Data.expressionName)
    }
  } else { Write-Host "  ext: YOK" }
}
