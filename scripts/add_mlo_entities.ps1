# add_mlo_entities.ps1 — bir MLO'nun ENTITY LISTESINE yeni obje ekler.
#
# NEDEN: MLO ic mekanina disaridan ymap ile prop KONULAMAZ — oda/portal
# sistemi eler (olculdu). Script'le spawn etmek de harita objesi
# uretmez (kapi sistemi bulamaz, fragment collision'i animasyonu takip
# etmez) ve 60 kisilik sunucuda her istemcide ayri spawn yuku olur.
# Dogru yol: objeyi MLO'nun KENDI listesine yazmak. Boylece objeyi MLO
# yerlestirir, sunucuya hicbir yuk binmez ve o MLO haritada kac yerde
# varsa (Fleeca 6 sube) hepsinde birden cikar.
#
# KOORDINAT: entity konumu MLO-YEREL uzayda olmali. Hucre verisi bir
# PARCA'nin (drawable) yerel uzayindaysa zincir:
#     panelLocal -> (parca pos/rot) -> mloLocal
# Bu script o donusumu yapar; dunya koordinati ISTEMEZ.
#
# Kullanim:
#   powershell -File add_mlo_entities.ps1 `
#       -YtypName v_int_10.ytyp -Mlo v_genbank -Part v_10_gen_country_bank `
#       -Model my_depobox -CellsJson <...>\depobox_cells_local.json `
#       -Count 20 -OutDir <...>\stream

param(
    [Parameter(Mandatory=$true)][string] $YtypName,
    [Parameter(Mandatory=$true)][string] $Mlo,
    [Parameter(Mandatory=$true)][string] $Part,
    [Parameter(Mandatory=$true)][string] $Model,
    [Parameter(Mandatory=$true)][string] $CellsJson,
    [Parameter(Mandatory=$true)][string] $OutDir,
    # ODA ADI — ZORUNLU DIYE DUSUN. MLO entity'si bir odanin
    # AttachedObjects listesinde KAYITLI DEGILSE oyun onu HIC OLUSTURMAZ
    # ve hicbir hata vermez. Sadece entities dizisine eklemek YETMEZ.
    [string] $Room = '',
    [int]    $Count = 20,
    # MLO IC MEKAN entity'si icin varsayilanlar. Bagimsiz ymap
    # degerlerini (flags=1572872, ORPHANHD) buraya koyarsan obje
    # SESSIZCE OLUSMAZ — ytyp yuklenir, entity listede gorunur, ama
    # oyunda hicbir sey cikmaz. Vanilla MLO entity'leri 18350080
    # kullaniyor (v_genbank'tan olculdu).
    [uint32] $Flags = 18350080,
    [single] $LodDist = -1,
    # Kutuyu duvardan disari kaydirma (m). 0 = doku duzleminde.
    [single] $Offset = 0.0,
    [string] $GtaFolder,
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker) { throw "CodeWalker.Core.dll bulunamadi." }
$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V klasoru bulunamadi." }

$cwDir = Split-Path $CodeWalker -Parent
$script:cwDir = $cwDir
[System.AppDomain]::CurrentDomain.add_AssemblyResolve([System.ResolveEventHandler]{
    param($sender, $e)
    $short = ($e.Name -split ',')[0]
    $p = Join-Path $script:cwDir "$short.dll"
    if (Test-Path -LiteralPath $p) { return [System.Reflection.Assembly]::LoadFrom($p) }
    return $null
})

if (-not (Test-Path -LiteralPath $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }

$src = @'
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using CodeWalker.GameFiles;
using SharpDX;

public static class MloEntityAdder
{
    public static uint Joaat(string s)
    {
        uint h = 0; s = s.ToLowerInvariant();
        for (int i = 0; i < s.Length; i++) { h += (byte)s[i]; h += h << 10; h ^= h >> 6; }
        h += h << 3; h ^= h >> 11; h += h << 15; return h;
    }

    class Cell { public float X, Y, Z, NX, NY; }

    static float Num(string s, string key)
    {
        int i = s.IndexOf(key);
        if (i < 0) return 0f;
        i = s.IndexOf(':', i) + 1;
        // Iki noktadan sonraki BOSLUGU atla — atlanmazsa tum degerler 0
        // okunur ve butun hucreler tek noktaya coker.
        while (i < s.Length && (s[i]==' '||s[i]=='\t'||s[i]=='\n'||s[i]=='\r')) i++;
        int j = i;
        while (j < s.Length && (char.IsDigit(s[j])||s[j]=='-'||s[j]=='.'||s[j]=='+'||s[j]=='e'||s[j]=='E')) j++;
        float v; float.TryParse(s.Substring(i, j-i).Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out v);
        return v;
    }

    static List<Cell> ReadCells(string path)
    {
        var list = new List<Cell>();
        var txt = File.ReadAllText(path);
        int i = txt.IndexOf("\"cells\"");
        if (i < 0) return list;
        foreach (var p in txt.Substring(i).Split('{'))
        {
            if (p.IndexOf("\"x\"") < 0) continue;
            var c = new Cell();
            c.X = Num(p,"\"x\""); c.Y = Num(p,"\"y\""); c.Z = Num(p,"\"z\"");
            c.NX = Num(p,"\"nx\""); c.NY = Num(p,"\"ny\"");
            list.Add(c);
        }
        return list;
    }

    static Quaternion Safe(Quaternion q)
    {
        if (q.Length() < 0.001f) return Quaternion.Identity;
        q.Normalize(); return q;
    }

    public static void Run(string gtaFolder, string ytypName, string mloName, string partName,
                           string model, string cellsJson, string outDir, int count,
                           float lodDist, float offset, uint flags, string room)
    {
        var cells = ReadCells(cellsJson);
        Console.WriteLine("[*] yerel hucre: {0}", cells.Count);
        if (cells.Count == 0) { Console.WriteLine("[!] hucre okunamadi"); return; }

        uint mloHash = Joaat(mloName), partHash = Joaat(partName), modelHash = Joaat(model);

        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        RpfFileEntry found = null;
        foreach (var rpf in man.AllRpfs) {
            foreach (var e in rpf.AllEntries) {
                var fe = e as RpfFileEntry;
                if (fe != null && string.Equals(fe.Name, ytypName, StringComparison.OrdinalIgnoreCase)) { found = fe; break; }
            }
            if (found != null) break;
        }
        if (found == null) { Console.WriteLine("[!] {0} bulunamadi", ytypName); return; }

        // YAMALAR UST USTE BINEBILMELI.
        // Her calismada vanilla RPF'ten okursak onceki yamayi EZERIZ.
        // (Gercek vaka: kapi degisimi yapildi, sonra ayni ytyp'ye kutu
        // eklenince kapilar vanilla'ya geri dondu.) Cikti klasorunde
        // dosya varsa ONDAN devam ederiz.
        var existing = Path.Combine(outDir, ytypName);
        var y = new YtypFile();
        if (File.Exists(existing))
        {
            y.Load(File.ReadAllBytes(existing));
            Console.WriteLine("[*] mevcut yamali dosyadan devam ediliyor: {0}", existing);
        }
        else
        {
            y.Load(found.File.ExtractFile(found), found);
            Console.WriteLine("[*] vanilla kaynaktan okundu");
        }

        MloArchetype target = null;
        Vector3 partPos = Vector3.Zero; Quaternion partRot = Quaternion.Identity;
        foreach (var a in y.AllArchetypes) {
            var m = a as MloArchetype;
            if (m == null || m.entities == null) continue;
            if (m._BaseArchetypeDef.name.Hash != mloHash) continue;
            target = m;
            foreach (var me in m.entities) {
                var d = me.Data;
                if (d.archetypeName.Hash != partHash) continue;
                partPos = d.position;
                partRot = Safe(new Quaternion(d.rotation.X, d.rotation.Y, d.rotation.Z, d.rotation.W));
                break;
            }
            break;
        }
        if (target == null) { Console.WriteLine("[!] MLO {0} bulunamadi", mloName); return; }

        // PARCA HEDEF MLO'DA OLMAYABILIR.
        // Ayni ic mekanin iki surumu olabiliyor (v_genbank ve
        // hei_generic_bank_dlc) ve ikisi AYNI MLO-yerel cerceveyi
        // paylasiyor — ayni prop ikisinde de ayni yerel konumda.
        // Referans parca hedefte yoksa TUM ytyp'lerde ariyoruz.
        if (partPos == Vector3.Zero)
        {
            Console.WriteLine("[*] parca '{0}' bu MLO'da yok — diger MLO'larda araniyor", partName);
            bool got = false;
            foreach (var rpf2 in man.AllRpfs) {
                foreach (var e2 in rpf2.AllEntries) {
                    var fe2 = e2 as RpfFileEntry;
                    if (fe2 == null || !fe2.NameLower.EndsWith(".ytyp")) continue;
                    byte[] d2; try { d2 = fe2.File.ExtractFile(fe2); } catch { continue; }
                    if (d2 == null || d2.Length == 0) continue;
                    var y2 = new YtypFile(); try { y2.Load(d2, fe2); } catch { continue; }
                    if (y2.AllArchetypes == null) continue;
                    foreach (var a2 in y2.AllArchetypes) {
                        var m2 = a2 as MloArchetype;
                        if (m2 == null || m2.entities == null) continue;
                        foreach (var me2 in m2.entities) {
                            if (me2.Data.archetypeName.Hash != partHash) continue;
                            partPos = me2.Data.position;
                            partRot = Safe(new Quaternion(me2.Data.rotation.X, me2.Data.rotation.Y,
                                                          me2.Data.rotation.Z, me2.Data.rotation.W));
                            Console.WriteLine("[*] parca {0} icinde bulundu", fe2.Name);
                            got = true; break;
                        }
                        if (got) break;
                    }
                    if (got) break;
                }
                if (got) break;
            }
            if (!got) { Console.WriteLine("[!] parca {0} hicbir yerde bulunamadi", partName); return; }
        }

        int before = target.entities.Length;
        Console.WriteLine("[*] MLO {0}: mevcut entity = {1}", mloName, before);
        Console.WriteLine("[*] parca yerel: ({0:0.###}, {1:0.###}, {2:0.###})", partPos.X, partPos.Y, partPos.Z);

        // Hucreleri ESIT ARALIKLA sec — hepsi bir kosede toplanmasin
        int step = Math.Max(1, cells.Count / Math.Max(1, count));
        var picked = new List<Cell>();
        for (int i = 0; i < cells.Count && picked.Count < count; i += step) picked.Add(cells[i]);

        var list = new List<MCEntityDef>(target.entities);
        foreach (var c in picked)
        {
            // panelLocal -> mloLocal
            var pl = new Vector3(c.X + c.NX * offset, c.Y + c.NY * offset, c.Z);
            var mlocal = partPos + Vector3.Transform(pl, partRot);

            // Duvarin disa bakan normali -> entity yonu (Z etrafinda)
            var nl = Vector3.Transform(new Vector3(c.NX, c.NY, 0f), partRot);
            double head = Math.Atan2(nl.Y, nl.X);
            var rot = Quaternion.RotationAxis(Vector3.UnitZ, (float)head);

            var ed = new CEntityDef();
            ed.archetypeName = new MetaHash(modelHash);
            ed.position = mlocal;
            // MLO entity rotasyonu TERS (conjugate) saklanir
            ed.rotation = new Vector4(-rot.X, -rot.Y, -rot.Z, rot.W);
            ed.scaleXY = 1.0f; ed.scaleZ = 1.0f;
            ed.parentIndex = -1;
            ed.lodDist = lodDist; ed.childLodDist = 0;
            ed.lodLevel = rage__eLodType.LODTYPES_DEPTH_ORPHANHD;
            ed.priorityLevel = rage__ePriorityLevel.PRI_REQUIRED;
            ed.flags = flags;
            ed.ambientOcclusionMultiplier = 255;
            ed.artificialAmbientOcclusion = 255;

            // MCEntityDef'in parametresiz yapicisi YOK.
            // ctor(ref CEntityDef, MloArchetype) kullanilir.
            list.Add(new MCEntityDef(ref ed, target));
        }

        int firstNew = target.entities.Length;
        target.entities = list.ToArray();
        Console.WriteLine("[+] {0} entity eklendi -> toplam {1}", picked.Count, target.entities.Length);

        // ── ODAYA BAGLA ──────────────────────────────────────────────
        // Bu adim atlanirsa obje SESSIZCE olusmaz: ytyp yuklenir, entity
        // listede gorunur, oyunda hicbir sey cikmaz. (Olculdu.)
        if (!string.IsNullOrEmpty(room) && target.rooms != null)
        {
            MCMloRoomDef rd = null;
            foreach (var r in target.rooms)
                if (string.Equals(r.RoomName, room, StringComparison.OrdinalIgnoreCase)) { rd = r; break; }

            if (rd == null)
            {
                Console.WriteLine("[X] '{0}' odasi bulunamadi. Mevcut odalar:", room);
                foreach (var r in target.rooms) Console.WriteLine("      {0}", r.RoomName);
                return;
            }

            var ao = new List<uint>(rd.AttachedObjects ?? new uint[0]);
            int had = ao.Count;
            for (int i = 0; i < picked.Count; i++) ao.Add((uint)(firstNew + i));
            rd.AttachedObjects = ao.ToArray();
            Console.WriteLine("[+] oda '{0}': attachedObjects {1} -> {2}", rd.RoomName, had, ao.Count);
        }
        else
        {
            Console.WriteLine("[!] -Room verilmedi — entity'ler HICBIR ODAYA bagli degil, oyunda GORUNMEZ.");
        }

        var outPath = Path.Combine(outDir, ytypName);
        var bytes = y.Save();
        File.WriteAllBytes(outPath, bytes);

        // GERI OKU VE DOGRULA
        var chk = new YtypFile();
        chk.Load(File.ReadAllBytes(outPath));
        int n = 0, mine = 0;
        foreach (var a in chk.AllArchetypes) {
            var m = a as MloArchetype;
            if (m == null || m.entities == null || m._BaseArchetypeDef.name.Hash != mloHash) continue;
            n = m.entities.Length;
            foreach (var me in m.entities) if (me.Data.archetypeName.Hash == modelHash) mine++;
        }
        Console.WriteLine("[+] yazildi: {0} ({1:N0} bayt)", outPath, bytes.Length);
        Console.WriteLine(n == before + picked.Count && mine == picked.Count
            ? string.Format("[+] dogrulama tamam: entity {0} -> {1}, '{2}' = {3} adet", before, n, model, mine)
            : string.Format("[X] DOGRULAMA HATASI: beklenen {0}, okunan {1} ('{2}' {3})", before + picked.Count, n, model, mine));
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

[MloEntityAdder]::Run($GtaFolder, $YtypName, $Mlo, $Part, $Model, $CellsJson, $OutDir, $Count, $LodDist, $Offset, $Flags, $Room)
