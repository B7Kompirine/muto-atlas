# patch_vanilla_ytyp.ps1 — vanilla bir .ytyp dosyasinin TAMAMINI kopyalayip
# icindeki belirli archetype'larin alanlarini degistirir ve AYNI ADLA yazar.
#
# NEDEN BU, make_ytyp_override.ps1'DEN FARKLI:
#   make_ytyp_override.ps1 YENI bir ytyp uretir (kendi adimizla yeni archetype).
#   O yol kendi modelimizi eklemek icin dogru, ama HARITADAKI mevcut objeyi
#   duzeltmek icin ise yaramaz: haritadaki entity hala vanilla archetype'a
#   bakar. Vanilla adiyla YENI bir ytyp eklemek de catisir — oyun ilk tanimi
#   zaten kaydetmistir.
#
#   Tutan yol: vanilla ytyp DOSYASINI ayni adla stream/ icine koymak.
#   FiveM stream klasorundeki dosyayi ad esleserek DEGISTIRIR; oyun bizim
#   surumumuzu yukler. Boylece haritadaki entity'nin kendisi duzelir —
#   obje spawn etmeye, gizlemeye, kapi sistemine elle kayit atmaya gerek
#   kalmaz. Ayni MLO haritada kac yerde varsa hepsinde birden gecerlidir.
#
# RISK: dosyanin TAMAMI degisir. Bu yuzden kaynak RPF'ten birebir okunur,
# sadece istenen alanlar yazilir ve yazdiktan sonra GERI OKUNUP kaynakla
# karsilastirilir (archetype sayisi, MLO oda/portal/entity sayilari).
# Karsilastirma tutmazsa dosya SILINIR — bozuk ytyp streamlemek MLO'yu
# komple bozar.
#
# Kullanim:
#   powershell -File patch_vanilla_ytyp.ps1 `
#       -YtypName int_lev_des.ytyp `
#       -Patch "v_ilev_gb_teldr=specialAttribute:7" `
#       -OutDir "<...>\stream"

param(
    [Parameter(Mandatory=$true)][string]   $YtypName,
    # "archetypeAdi=alan:deger" biciminde, virgulle birden fazla.
    # Desteklenen alanlar: specialAttribute, flags, lodDist
    [string[]] $Patch = @(),
    # "eskiModel=yeniModel" — MLO'nun ENTITY listesinde model adini degistirir.
    #
    # NEDEN GEREKLI: MLO ic mekanina disaridan ymap ile prop koyulamaz; oda/
    # portal sistemi onu eler. Ic mekandaki bir objeyi kendi modelimizle
    # degistirmenin tek dogru yolu MLO'nun kendi entity listesini duzeltmek.
    # Boylece objeyi MLO'nun KENDISI yerleştirir: gizleme, ymap, spawn yok
    # ve o MLO haritada kac yerde varsa hepsinde birden gecerli olur.
    [string[]] $SwapEntity = @(),
    [Parameter(Mandatory=$true)][string]   $OutDir,
    [string] $GtaFolder,
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

$CodeWalker = & "$PSScriptRoot\yol.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) { throw "CodeWalker.Core.dll bulunamadi." }

$GtaFolder = & "$PSScriptRoot\yol.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V klasoru bulunamadi." }

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }

$cwDir = Split-Path $CodeWalker -Parent
$script:cwDir = $cwDir
[System.AppDomain]::CurrentDomain.add_AssemblyResolve([System.ResolveEventHandler]{
    param($sender, $e)
    $short = ($e.Name -split ',')[0]
    $p = Join-Path $script:cwDir "$short.dll"
    if (Test-Path $p) { return [System.Reflection.Assembly]::LoadFrom($p) }
    return $null
})

$src = @'
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using CodeWalker.GameFiles;

public static class YtypPatcher
{
    public static uint Joaat(string s)
    {
        uint h = 0; s = s.ToLowerInvariant();
        for (int i = 0; i < s.Length; i++) { h += (byte)s[i]; h += h << 10; h ^= h >> 6; }
        h += h << 3; h ^= h >> 11; h += h << 15; return h;
    }

    // MLO'nun ic yapisini sayarak imzasini cikarir. Round-trip sonrasi
    // bu imza degistiyse kayit bozulmus demektir.
    static string Signature(YtypFile y)
    {
        int arch = 0, mlo = 0, rooms = 0, portals = 0, ents = 0, esets = 0;
        if (y.AllArchetypes != null)
        {
            arch = y.AllArchetypes.Length;
            foreach (var a in y.AllArchetypes)
            {
                var m = a as MloArchetype;
                if (m == null) continue;
                mlo++;
                if (m.rooms != null)      rooms   += m.rooms.Length;
                if (m.portals != null)    portals += m.portals.Length;
                if (m.entities != null)   ents    += m.entities.Length;
                if (m.entitySets != null) esets   += m.entitySets.Length;
            }
        }
        return string.Format(CultureInfo.InvariantCulture,
            "arch={0} mlo={1} rooms={2} portals={3} entities={4} entitySets={5}",
            arch, mlo, rooms, portals, ents, esets);
    }

    public static void Run(string gtaFolder, string ytypName, string[] patches, string outDir, string[] swaps)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        // Istenen degisiklikleri ayristir: "ad=alan:deger"
        var want = new Dictionary<uint, List<KeyValuePair<string,string>>>();
        var names = new Dictionary<uint, string>();
        foreach (var p in patches)
        {
            var eq = p.IndexOf('=');
            if (eq < 0) { Console.WriteLine("[!] anlasilmadi: {0}", p); continue; }
            var an = p.Substring(0, eq).Trim();
            var rest = p.Substring(eq + 1).Trim();
            var co = rest.IndexOf(':');
            if (co < 0) { Console.WriteLine("[!] anlasilmadi: {0}", p); continue; }
            uint h = Joaat(an);
            names[h] = an;
            if (!want.ContainsKey(h)) want[h] = new List<KeyValuePair<string,string>>();
            want[h].Add(new KeyValuePair<string,string>(rest.Substring(0, co).Trim(),
                                                       rest.Substring(co + 1).Trim()));
        }

        // Kaynak dosyayi RPF'te bul
        RpfFileEntry found = null;
        foreach (var rpf in man.AllRpfs)
        {
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null) continue;
                if (string.Equals(fe.Name, ytypName, StringComparison.OrdinalIgnoreCase)) { found = fe; break; }
            }
            if (found != null) break;
        }
        if (found == null) { Console.WriteLine("[!] {0} RPF'lerde bulunamadi.", ytypName); return; }

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
        string sigBefore = Signature(y);
        Console.WriteLine("[*] kaynak: {0}", found.Path);
        Console.WriteLine("[*] imza  : {0}", sigBefore);

        // Alanlari degistir. AllArchetypes ELEMANLARI struct dondurur;
        // degisikligin kalici olmasi icin archetype nesnesine Init ile
        // geri yazmak gerekiyor.
        int changed = 0;
        foreach (var a in y.AllArchetypes)
        {
            var def = a._BaseArchetypeDef;
            if (!want.ContainsKey(def.name.Hash)) continue;

            foreach (var kv in want[def.name.Hash])
            {
                switch (kv.Key)
                {
                    case "specialAttribute":
                        Console.WriteLine("[+] {0}.specialAttribute {1} -> {2}", names[def.name.Hash], def.specialAttribute, kv.Value);
                        def.specialAttribute = uint.Parse(kv.Value, CultureInfo.InvariantCulture);
                        break;
                    case "flags":
                        Console.WriteLine("[+] {0}.flags {1} -> {2}", names[def.name.Hash], def.flags, kv.Value);
                        def.flags = uint.Parse(kv.Value, CultureInfo.InvariantCulture);
                        break;
                    case "lodDist":
                        Console.WriteLine("[+] {0}.lodDist {1} -> {2}", names[def.name.Hash], def.lodDist, kv.Value);
                        def.lodDist = float.Parse(kv.Value, CultureInfo.InvariantCulture);
                        break;
                    default:
                        Console.WriteLine("[!] desteklenmeyen alan: {0}", kv.Key);
                        break;
                }
            }
            a.Init(y, ref def);
            changed++;
        }

        // ── MLO ENTITY MODEL DEGISIMI ────────────────────────────────
        var swapMap = new Dictionary<uint, KeyValuePair<string,string>>();
        foreach (var s in swaps)
        {
            var eq = s.IndexOf('=');
            if (eq < 0) { Console.WriteLine("[!] anlasilmadi: {0}", s); continue; }
            var oldN = s.Substring(0, eq).Trim();
            var newN = s.Substring(eq + 1).Trim();
            swapMap[Joaat(oldN)] = new KeyValuePair<string,string>(oldN, newN);
        }

        int swapped = 0;
        if (swapMap.Count > 0)
        {
            foreach (var a in y.AllArchetypes)
            {
                var m = a as MloArchetype;
                if (m == null || m.entities == null) continue;
                foreach (var me in m.entities)
                {
                    var d = me.Data;
                    KeyValuePair<string,string> sw;
                    if (!swapMap.TryGetValue(d.archetypeName.Hash, out sw)) continue;
                    // MCEntityDef.Data bir STRUCT dondurur; kopyala-degistir-geri yaz
                    d.archetypeName = new MetaHash(Joaat(sw.Value));
                    me.Data = d;
                    swapped++;
                    Console.WriteLine("[+] MLO {0}: entity {1} -> {2}  (pos {3})",
                        m._BaseArchetypeDef.name, sw.Key, sw.Value, d.position);
                }
            }
            changed += swapped;
        }

        if (changed == 0) { Console.WriteLine("[!] hicbir degisiklik yapilmadi — dosya yazilmadi."); return; }

        var outPath = Path.Combine(outDir, ytypName);
        var outBytes = y.Save();
        File.WriteAllBytes(outPath, outBytes);

        // ---- GERI OKU VE DOGRULA ----
        var check = new YtypFile();
        check.Load(File.ReadAllBytes(outPath));
        string sigAfter = Signature(check);
        Console.WriteLine("[*] yazilan imza: {0}", sigAfter);

        bool ok = (sigBefore == sigAfter);
        if (ok)
        {
            foreach (var a in check.AllArchetypes)
            {
                var def = a._BaseArchetypeDef;
                if (want.ContainsKey(def.name.Hash))
                    Console.WriteLine("    dogrulama: {0} specialAttribute={1} flags={2} lodDist={3}",
                        names[def.name.Hash], def.specialAttribute, def.flags, def.lodDist);
            }
            // Model degisimi gercekten dosyaya gitti mi?
            if (swapMap.Count > 0)
            {
                int seen = 0, leftover = 0;
                foreach (var a in check.AllArchetypes)
                {
                    var m = a as MloArchetype;
                    if (m == null || m.entities == null) continue;
                    foreach (var me in m.entities)
                    {
                        var h = me.Data.archetypeName.Hash;
                        if (swapMap.ContainsKey(h)) leftover++;
                        foreach (var kv in swapMap)
                            if (h == Joaat(kv.Value.Value)) seen++;
                    }
                }
                Console.WriteLine("    dogrulama: yeni model {0} entity'de, eski model {1} entity'de kaldi", seen, leftover);
                if (seen != swapped || leftover != 0) ok = false;
            }
        }

        if (!ok)
        {
            File.Delete(outPath);
            Console.WriteLine("[X] IMZA TUTMADI — dosya SILINDI. Bozuk ytyp streamlemek MLO'yu bozar.");
            return;
        }

        Console.WriteLine("[+] yazildi: {0}  ({1} bayt, {2} archetype degisti)", outPath, outBytes.Length, changed);
        Console.WriteLine("[i] fxmanifest'e SADECE files{{}} olarak ekle — data_file DLC_ITYP_REQUEST EKLEME.");
        Console.WriteLine("    Bu bir vanilla dosya DEGISIMIDIR, yeni bir ityp kaydi degil.");
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

[YtypPatcher]::Run($GtaFolder, $YtypName, $Patch, $OutDir, $SwapEntity)
