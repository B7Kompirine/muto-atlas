# make_ytyp_override.ps1 — vanilla bir archetype'i kopyalayip TEK alanini
# degistirerek override .ytyp uretir.
#
# NEDEN: bir prop/kapi yanlis tanimlanmissa (or. kapi olmasi gereken obje
# specialAttribute=0) tek dogru cozum ytyp seviyesinde duzeltmektir.
# Bu script kaynagi RPF'ten okur, alanlari BIREBIR kopyalar, sadece
# istenen degeri degistirir — uydurma alan olmaz.
#
# Kullanim:
#   powershell -File make_ytyp_override.ps1 `
#       -Models v_ilev_gb_teldr,v_ilev_gb_vauldr `
#       -SpecialAttribute 7 `
#       -YtypName muto_fleeca_doors `
#       -OutFile "<...>\stream\muto_fleeca_doors.ytyp"

param(
    [Parameter(Mandatory=$true)][string[]] $Models,
    [int]    $SpecialAttribute = 7,
    [Parameter(Mandatory=$true)][string] $YtypName,
    [Parameter(Mandatory=$true)][string] $OutFile,
    # Vanilla archetype'i EZMEK yerine KENDI ADIMIZLA yeni archetype uret.
    # Ezme yolu (ayni ad) oyunun zaten kaydettigi tanimla catisiyor ve
    # tutmuyor; yeni ad catismasiz eklenir. Model dosyasi da bu adla
    # export edilmis olmali.
    [string] $RenameTo,
    # Ozel prop'ta doku/collision .ydr icine gomulu olur -> sozlukler 0.
    [switch] $ClearDicts,
    # .yft (fragment) icin ASSET_TYPE_FRAGMENT gerekir; .ydr icin ASSET_TYPE_DRAWABLE.
    # Kaynak archetype drawable ise ve biz fragment ürettiysek bunu DEGISTIRMEK sart,
    # yoksa oyun modeli drawable olarak yukler ve per-bone collision devreye girmez.
    [ValidateSet('ASSET_TYPE_UNINITIALIZED','ASSET_TYPE_FRAGMENT','ASSET_TYPE_DRAWABLE',
                 'ASSET_TYPE_DRAWABLEDICTIONARY','ASSET_TYPE_ASSETLESS')]
    [string] $AssetType,
    # Fragment'lerde physicsDictionary modelin KENDI adini gosterir (0 degil).
    # Calisan referans (mairon_kapili_box) boyle; ClearDicts'ten sonra uygulanir.
    [switch] $PhysicsDictSelf,
    [uint32] $Flags = 0,
    [single] $LodDist = 0,
    # Klip sozlugu adi (CIPLAK ad, uzantisiz). Animasyonlu prop'larda sart.
    [string] $ClipDict,
    # Expression extension: .yed dosyasini arketipe baglar.
    # CIPLAK AD verilir — oyun "pack:/" ve ".expr" kismini kendisi ekler.
    # "pack:/x.expr" yazarsan expression HIC yuklenmez ama mesh animasyonu
    # calismaya devam eder; hatayi fark etmek cok zor olur.
    [string] $Expression,
    [string] $GtaFolder,
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

$CodeWalker = & "$PSScriptRoot\yol.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) { throw "CodeWalker.Core.dll bulunamadi." }

$GtaFolder = & "$PSScriptRoot\yol.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V klasoru bulunamadi." }

$cwDir = Split-Path $CodeWalker -Parent
$script:cwDir = $cwDir
[System.AppDomain]::CurrentDomain.add_AssemblyResolve([System.ResolveEventHandler]{
    param($sender, $e)
    $short = ($e.Name -split ',')[0]
    $p = Join-Path $script:cwDir "$short.dll"
    if (Test-Path $p) { return [System.Reflection.Assembly]::LoadFrom($p) }
    return $null
})

$outDir = Split-Path $OutFile -Parent
if ($outDir -and -not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }

$src = @'
using System;
using System.Collections.Generic;
using System.IO;
using CodeWalker.GameFiles;

public static class YtypOverride
{
    public static uint Joaat(string s)
    {
        uint h = 0; s = s.ToLowerInvariant();
        for (int i = 0; i < s.Length; i++) { h += (byte)s[i]; h += h << 10; h ^= h >> 6; }
        h += h << 3; h ^= h >> 11; h += h << 15; return h;
    }

    public static void Run(string gtaFolder, string[] models, int specialAttr, string ytypName, string outFile,
                           string renameTo, bool clearDicts, uint flags, float lodDist,
                           string assetType, bool physicsDictSelf,
                           string clipDict, string expression)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        var want = new Dictionary<uint, string>();
        foreach (var m in models) want[Joaat(m)] = m;

        var found = new Dictionary<uint, CBaseArchetypeDef>();
        var srcYtyp = new Dictionary<uint, string>();

        foreach (var rpf in man.AllRpfs)
        {
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null || !fe.NameLower.EndsWith(".ytyp")) continue;
                byte[] data;
                try { data = fe.File.ExtractFile(fe); } catch { continue; }
                if (data == null || data.Length == 0) continue;
                var y = new YtypFile();
                try { y.Load(data, fe); } catch { continue; }
                if (y.AllArchetypes == null) continue;
                foreach (var a in y.AllArchetypes)
                {
                    var d = a._BaseArchetypeDef;
                    if (!want.ContainsKey(d.name.Hash) || found.ContainsKey(d.name.Hash)) continue;
                    found[d.name.Hash] = d;
                    srcYtyp[d.name.Hash] = fe.Name;
                }
            }
            if (found.Count == want.Count) break;
        }

        foreach (var kv in want)
            if (!found.ContainsKey(kv.Key))
                Console.WriteLine("[!] BULUNAMADI: {0}", kv.Value);
        if (found.Count == 0) { Console.WriteLine("[!] Hicbir archetype bulunamadi, cikiliyor."); return; }

        var outYtyp = new YtypFile();
        outYtyp.Name = ytypName;
        outYtyp.NameHash = Joaat(ytypName);
        var mt = outYtyp.CMapTypes;   // struct; dogrudan kopyala-degistir-geri yaz
        mt.name = new MetaHash(Joaat(ytypName));
        outYtyp._CMapTypes = mt;

        foreach (var kv in found)
        {
            var def = kv.Value;
            uint before = def.specialAttribute;
            def.specialAttribute = (uint)specialAttr;

            string outName = want[kv.Key];
            if (!string.IsNullOrEmpty(renameTo))
            {
                outName = renameTo;
                var nh = new MetaHash(Joaat(renameTo));
                def.name = nh;
                def.assetName = nh;      // .ydr dosya adiyla ayni olmali
            }
            if (clearDicts)
            {
                // Doku ve collision .ydr icine gomulu -> dis sozluk yok
                def.physicsDictionary = new MetaHash(0);
                def.textureDictionary = new MetaHash(0);
            }
            if (physicsDictSelf)
            {
                // Fragment: physicsDictionary kendi adini gosterir
                def.physicsDictionary = new MetaHash(Joaat(outName));
            }
            if (!string.IsNullOrEmpty(assetType))
            {
                // assetType bir PROPERTY (alan degil), tipi rage__fwArchetypeDef__eAssetType.
                def.assetType = (rage__fwArchetypeDef__eAssetType)
                    Enum.Parse(typeof(rage__fwArchetypeDef__eAssetType), assetType);
            }
            if (!string.IsNullOrEmpty(clipDict))
                def.clipDictionary = new MetaHash(Joaat(clipDict));
            if (flags != 0) def.flags = flags;
            if (lodDist > 0) def.lodDist = lodDist;

            var na = outYtyp.AddArchetype();
            na.Init(outYtyp, ref def);

            // ── EXPRESSION EXTENSION ──────────────────────────────────
            // .yed'i arketipe baglar. Collision'in animasyonu takip etmesi
            // bu bagla calisiyor; extension yoksa mesh oynar, carpisma durur.
            if (!string.IsNullOrEmpty(expression))
            {
                // Data salt-okunur property; alttaki _Data ALANINA yaziyoruz.
                var ext = new MCExtensionDefExpression();
                var ed = new CExtensionDefExpression();
                ed.name = new MetaHash(Joaat(outName));
                ed.expressionDictionaryName = new MetaHash(Joaat(expression));
                ed.expressionName = new MetaHash(Joaat(expression));
                ed.creatureMetadataName = new MetaHash(0);
                ed.initialiseOnCollision = 0;
                ext._Data = ed;
                na.Extensions = new MetaWrapper[] { ext };
                Console.WriteLine("      expression extension -> dict='{0}' name='{0}' (hash {1})",
                    expression, Joaat(expression));
            }

            Console.WriteLine("[+] {0,-22} -> {1,-18} specialAttribute {2} -> {3}   (kaynak: {4})",
                want[kv.Key], outName, before, specialAttr, srcYtyp[kv.Key]);
            Console.WriteLine("      bbMin={0}  bbMax={1}  flags={2}  physics={3}  assetType={4}  lodDist={5}",
                def.bbMin, def.bbMax, def.flags, def.physicsDictionary, def.assetType, def.lodDist);
        }

        byte[] outBytes = outYtyp.Save();
        File.WriteAllBytes(outFile, outBytes);
        Console.WriteLine("[+] yazildi: {0}  ({1} bayt, {2} archetype)", outFile, outBytes.Length, found.Count);
        Console.WriteLine("[i] ytyp adi: {0}  (hash {1})", ytypName, Joaat(ytypName));
    }
}
'@

# 'System.Collections'/'System.Runtime'/'System.Console' SART: PowerShell 7 (.NET 8+)
# altinda bu tipler netstandard'dan FORWARD edilmis durumda; referans verilmezse
# Add-Type "CS1069: type has been forwarded" / "CS0103: Console does not exist"
# ile coker. Windows PowerShell 5.1'de sorun cikmaz, PS7'de her seferinde cikar.
$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard', 'mscorlib',
          'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[YtypOverride]::Run($GtaFolder, $Models, $SpecialAttribute, $YtypName, $OutFile,
                    $RenameTo, $ClearDicts.IsPresent, $Flags, $LodDist,
                    $AssetType, $PhysicsDictSelf.IsPresent, $ClipDict, $Expression)
