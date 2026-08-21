# make_prop_ymap.ps1 — bir VANILLA prop'un haritadaki tum yerlesimlerini
# bulup, ayni konum/donusle KENDI prop'umuzu koyan bir .ymap uretir.
#
# NEDEN GEREKLI: script'le uretilen obje (CreateObject) HARITA OBJESI
# degildir. Olculen sonuclar:
#   - Kapi sistemi onu bulamaz; kapi serbest prop gibi davranip dustu.
#   - Fragment'in per-bone carpismasi animasyonu takip etmedi.
# Calisan referans (mairon_panel) prop'unu ymap ile koyuyor:
#   lodLevel=LODTYPES_DEPTH_ORPHANHD  priority=PRI_REQUIRED  flags=1572872
#   contentFlags=65
# Bu script ayni yerlesim bicimini uretir.
#
# KONUM/DONUS NEREDEN: prop bir MLO'nun icindeyse konumu MLO archetype'inin
# entity listesinde YEREL olarak durur. Zincir:
#   yerel -> (MLO instance pos/rot) -> dunya
# Ayni MLO haritada kac yerde varsa (Fleeca 6 sube) hepsi icin ayri ayri
# yerlesim yazilir. Disaridaki proplar icin ymap'ler dogrudan taranir.
#
# Kullanim:
#   powershell -File make_prop_ymap.ps1 `
#       -SourceModel v_ilev_gb_vauldr -PlaceModel muto_vauldr `
#       -YmapName muto_vauldr_placement `
#       -OutFile "<...>\stream\muto_vauldr_placement.ymap"

param(
    [Parameter(Mandatory=$true)][string] $SourceModel,
    [Parameter(Mandatory=$true)][string] $PlaceModel,
    [Parameter(Mandatory=$true)][string] $YmapName,
    [Parameter(Mandatory=$true)][string] $OutFile,
    [single] $LodDist = 160,
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
using System.Globalization;
using System.IO;
using CodeWalker.GameFiles;
using SharpDX;

public static class PropYmapMaker
{
    public static uint Joaat(string s)
    {
        uint h = 0; s = s.ToLowerInvariant();
        for (int i = 0; i < s.Length; i++) { h += (byte)s[i]; h += h << 10; h ^= h >> 6; }
        h += h << 3; h ^= h >> 11; h += h << 15; return h;
    }

    static Quaternion Safe(Quaternion q)
    {
        if (q.Length() < 0.001f) return Quaternion.Identity;
        q.Normalize(); return q;
    }

    public static void Run(string gtaFolder, string sourceModel, string placeModel,
                           string ymapName, string outFile, float lodDist)
    {
        uint srcHash   = Joaat(sourceModel);
        uint placeHash = Joaat(placeModel);

        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        // 1) Prop'u iceren MLO archetype'lerini ve YEREL yerlesimini bul.
        //    Ayrica prop'un KENDI archetype'inin kusat yaricapini al —
        //    ymap'in entity extent'leri bundan hesaplanacak.
        float bsRadius = 0f;
        var localPlacements = new List<Tuple<uint, Vector3, Quaternion>>(); // mloHash, localPos, localRot
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
                    if (a._BaseArchetypeDef.name.Hash == srcHash && bsRadius <= 0f)
                        bsRadius = a._BaseArchetypeDef.bsRadius;

                    var m = a as MloArchetype;
                    if (m == null || m.entities == null) continue;
                    foreach (var me in m.entities)
                    {
                        var d = me.Data;
                        if (d.archetypeName.Hash != srcHash) continue;
                        localPlacements.Add(Tuple.Create(
                            m._BaseArchetypeDef.name.Hash,
                            (Vector3)d.position,
                            Safe(new Quaternion(d.rotation.X, d.rotation.Y, d.rotation.Z, d.rotation.W))));
                    }
                }
            }
        }
        Console.WriteLine("[*] MLO icinde yerel yerlesim: {0}", localPlacements.Count);

        // 2) O MLO'larin dunya yerlesimlerini bul ve yerel -> dunya cevir
        var world = new List<Tuple<Vector3, Quaternion>>();
        var seen = new HashSet<string>();

        foreach (var rpf in man.AllRpfs)
        {
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null || !fe.NameLower.EndsWith(".ymap")) continue;
                byte[] data;
                try { data = fe.File.ExtractFile(fe); } catch { continue; }
                if (data == null || data.Length == 0) continue;
                var y = new YmapFile();
                try { y.Load(data, fe); } catch { continue; }

                // 2a) MLO ornekleri
                if (y.CMloInstanceDefs != null)
                {
                    foreach (var mi in y.CMloInstanceDefs)
                    {
                        var ced = mi.CEntityDef;
                        foreach (var lp in localPlacements)
                        {
                            if (ced.archetypeName.Hash != lp.Item1) continue;
                            var mloPos = (Vector3)ced.position;
                            var mloRot = Safe(new Quaternion(ced.rotation.X, ced.rotation.Y, ced.rotation.Z, ced.rotation.W));
                            var wp = mloPos + Vector3.Transform(lp.Item2, mloRot);
                            var wr = mloRot * lp.Item3;
                            string k = string.Format(CultureInfo.InvariantCulture, "{0:0.00}_{1:0.00}_{2:0.00}", wp.X, wp.Y, wp.Z);
                            if (seen.Add(k)) world.Add(Tuple.Create(wp, wr));
                        }
                    }
                }

                // 2b) Dogrudan haritaya konmus olabilir (MLO disi)
                if (y.CEntityDefs != null)
                {
                    foreach (var ced in y.CEntityDefs)
                    {
                        if (ced.archetypeName.Hash != srcHash) continue;
                        var wp = (Vector3)ced.position;
                        var wr = Safe(new Quaternion(ced.rotation.X, ced.rotation.Y, ced.rotation.Z, ced.rotation.W));
                        string k = string.Format(CultureInfo.InvariantCulture, "{0:0.00}_{1:0.00}_{2:0.00}", wp.X, wp.Y, wp.Z);
                        if (seen.Add(k)) world.Add(Tuple.Create(wp, wr));
                    }
                }
            }
        }

        Console.WriteLine("[*] dunya yerlesimi: {0}", world.Count);
        if (world.Count == 0) { Console.WriteLine("[!] Yerlesim bulunamadi, ymap yazilmadi."); return; }

        // 3) HER YERLESIM ICIN AYRI YMAP.
        //
        // NEDEN AYRI: oyun ymap'leri EXTENT'lerine gore streamler. 6 subeyi
        // tek dosyaya koyunca sinirlar tum haritayi kapladi
        // (X -2958..1175, Y -1044..2710) ve ymap oyun ici hic yuklenmedi —
        // vanilla gizleniyor, bizimki gelmiyordu, kapi ortadan kayboluyordu.
        // Calisan referansin ymap'i ~1 metrelik bir kutu ve TEK entity
        // iceriyor; ayni bicime geciyoruz.
        int written = 0;
        string baseNoExt = Path.Combine(
            Path.GetDirectoryName(outFile),
            Path.GetFileNameWithoutExtension(outFile));

        for (int wi = 0; wi < world.Count; wi++)
        {
            var w = world[wi];
            string perName = string.Format("{0}_{1}", ymapName, wi + 1);
            string perPath = string.Format("{0}_{1}.ymap", baseNoExt, wi + 1);

            var outY = new YmapFile();
            outY.Name = perName;

            var ents = new List<CEntityDef>();
            var ed = new CEntityDef();
            ed.archetypeName = new MetaHash(placeHash);
            ed.position = w.Item1;
            ed.rotation = new Vector4(w.Item2.X, w.Item2.Y, w.Item2.Z, w.Item2.W);
            ed.scaleXY = 1.0f;
            ed.scaleZ = 1.0f;
            ed.parentIndex = -1;
            ed.lodDist = lodDist;
            ed.childLodDist = 0;
            ed.lodLevel = rage__eLodType.LODTYPES_DEPTH_ORPHANHD;   // referansla ayni
            ed.numChildren = 0;
            ed.priorityLevel = rage__ePriorityLevel.PRI_REQUIRED;          // referansla ayni
            ed.flags = 1572872;                                      // referansla ayni
            ed.ambientOcclusionMultiplier = 255;
            ed.artificialAmbientOcclusion = 255;
            ents.Add(ed);

            // CEntityDefs'i DOGRUDAN yazmak yetmiyor: Save() seri hale
            // getirirken AllEntities'ten uretiyor (BuildCEntityDefs).
            // Dogrudan yazinca dosya olusuyor ama icinde 0 entity oluyordu.
            var yents = new List<YmapEntityDef>();
            for (int i = 0; i < ents.Count; i++)
            {
                var e2 = ents[i];
                yents.Add(new YmapEntityDef(outY, i, ref e2));
            }
            outY.AllEntities  = yents.ToArray();
            outY.RootEntities = yents.ToArray();
            outY.BuildCEntityDefs();

            // CMapData alanlarini EN SON yaz.
            //
            // CalcFlags() CAGIRMIYORUZ: contentFlags'i yeniden hesaplayip
            // 65'i 1'e dusuruyordu.
            //
            // CalcExtents() de KULLANILMIYOR: archetype bu baglamda cozulmedigi
            // icin entity kutusunu SIFIR BOYUTLU birakiyordu (0x0x0 m).
            // Sifir kutulu ymap streamlenmiyor. Extent'leri prop'un kusat
            // yaricapindan elle kuruyoruz; streaming extent'i de referanstaki
            // gibi lodDist kadar disari tasiyoruz
            // (referans: streaming = entities +- 160).
            float r = bsRadius > 0f ? bsRadius : 2.0f;
            var p = w.Item1;
            var eMin = new Vector3(p.X - r, p.Y - r, p.Z - r);
            var eMax = new Vector3(p.X + r, p.Y + r, p.Z + r);

            var cmd = outY.CMapData;
            cmd.name                = new MetaHash(Joaat(perName));
            cmd.parent              = new MetaHash(0);
            cmd.flags               = 0;
            cmd.contentFlags        = 65;      // referansla ayni
            cmd.entitiesExtentsMin  = eMin;
            cmd.entitiesExtentsMax  = eMax;
            cmd.streamingExtentsMin = new Vector3(eMin.X - lodDist, eMin.Y - lodDist, eMin.Z - lodDist);
            cmd.streamingExtentsMax = new Vector3(eMax.X + lodDist, eMax.Y + lodDist, eMax.Z + lodDist);
            outY.CMapData           = cmd;

            var bytes = outY.Save();
            File.WriteAllBytes(perPath, bytes);

            // Geri oku ve dogrula
            var chk = RpfFile.GetResourceFile<YmapFile>(File.ReadAllBytes(perPath));
            int n = (chk != null && chk.CEntityDefs != null) ? chk.CEntityDefs.Length : 0;
            var cc = chk.CMapData;
            var ext = cc.entitiesExtentsMax - cc.entitiesExtentsMin;

            Console.WriteLine("  [{0}] {1}  ({2:0.###}, {3:0.###}, {4:0.###})  entity={5} contentFlags={6} kutu={7:0.0}x{8:0.0}x{9:0.0} m",
                wi + 1, Path.GetFileName(perPath), w.Item1.X, w.Item1.Y, w.Item1.Z,
                n, cc.contentFlags, ext.X, ext.Y, ext.Z);

            if (n != 1 || cc.contentFlags != 65)
                Console.WriteLine("      [X] DOGRULAMA HATASI");
            else
                written++;
        }

        Console.WriteLine("[+] {0}/{1} ymap yazildi -> {2}", written, world.Count, Path.GetDirectoryName(outFile));
    }
}
'@

# 'System.Collections'/'System.Runtime'/'System.Console' SART: PowerShell 7 (.NET 8+)
# altinda bu tipler netstandard'dan FORWARD edilmis durumda; referans verilmezse
# Add-Type "CS1069: type has been forwarded" / "CS0103: Console does not exist"
# ile coker. Windows PowerShell 5.1'de sorun cikmaz, PS7'de her seferinde cikar.
$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[PropYmapMaker]::Run($GtaFolder, $SourceModel, $PlaceModel, $YmapName, $OutFile, $LodDist)
