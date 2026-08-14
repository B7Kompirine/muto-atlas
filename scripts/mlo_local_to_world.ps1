# mlo_local_to_world.ps1 — bir MLO ic mekanindaki YEREL koordinatlari
# tum dunya yerlesimlerine cevirir.
#
# NEDEN: bir MLO'nun icindeki bir noktayi (or. kasa duvarindaki kutu hucresi)
# Blender'da modelin yerel uzayinda buluyoruz. Oyunda kullanmak icin o nokta
# once ic mekandaki PARCA'nin (drawable entity) yerlesiminden, sonra MLO'nun
# dunya yerlesiminden gecmeli. Ayni MLO haritada birden fazla yerde olabilir
# (Fleeca 6 subede) — hepsi icin ayri ayri hesaplanir.
#
# ZINCIR:  panelLocal -> (parca pos/rot) -> mloLocal -> (mlo pos/rot) -> world
# Ham quaternion dogru konvansiyon; build_entities.ps1 ile ayni matematik
# (v_ilev_gb_teldr @ Legion ile dogrulandi).
#
# Kullanim:
#   powershell -File mlo_local_to_world.ps1 `
#       -Mlo v_genbank -Part v_10_gen_country_bank `
#       -CellsJson <...\depobox_cells_local.json> -OutJson <...\cells_world.json>

param(
    [Parameter(Mandatory=$true)][string] $Mlo,
    [Parameter(Mandatory=$true)][string] $Part,
    [Parameter(Mandatory=$true)][string] $CellsJson,
    [Parameter(Mandatory=$true)][string] $OutJson,
    [string] $GtaFolder,
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

if (-not $CodeWalker) {
    $CodeWalker = @(
        "$env:USERPROFILE\Desktop\FiveM\CodeWalker30_dev46\CodeWalker.Core.dll",
        "$env:USERPROFILE\Desktop\CodeWalker\CodeWalker.Core.dll"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) { throw "CodeWalker.Core.dll bulunamadi." }
if (-not $GtaFolder) {
    $GtaFolder = @(
        'C:\Program Files\Epic Games\GTAV',
        'C:\Program Files\Rockstar Games\Grand Theft Auto V',
        'C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V'
    ) | Where-Object { Test-Path (Join-Path $_ 'GTA5.exe') } | Select-Object -First 1
}
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

$src = @'
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using CodeWalker.GameFiles;
using SharpDX;

public static class MloToWorld
{
    public static uint Joaat(string s)
    {
        uint h = 0; s = s.ToLowerInvariant();
        for (int i = 0; i < s.Length; i++) { h += (byte)s[i]; h += h << 10; h ^= h >> 6; }
        h += h << 3; h ^= h >> 11; h += h << 15; return h;
    }

    class Cell { public float X, Y, Z, NX, NY; }

    // Cok kucuk bir JSON okuyucu: bu dosyanin sekli sabit (duz sayi alanlari).
    static List<Cell> ReadCells(string path)
    {
        var list = new List<Cell>();
        var txt = File.ReadAllText(path);
        int i = txt.IndexOf("\"cells\"");
        if (i < 0) return list;
        var parts = txt.Substring(i).Split('{');
        foreach (var p in parts)
        {
            if (p.IndexOf("\"x\"") < 0) continue;
            var c = new Cell();
            c.X  = Num(p, "\"x\"");  c.Y  = Num(p, "\"y\"");  c.Z  = Num(p, "\"z\"");
            c.NX = Num(p, "\"nx\""); c.NY = Num(p, "\"ny\"");
            list.Add(c);
        }
        return list;
    }

    static float Num(string s, string key)
    {
        int i = s.IndexOf(key);
        if (i < 0) return 0f;
        i = s.IndexOf(':', i) + 1;
        // Iki noktadan sonraki BOSLUGU atla. Atlamayinca tarayici hemen
        // durup bos string donuyordu -> her alan 0 okunuyor -> tum hucreler
        // tek noktaya cokuyordu. (Ilk calistirmadaki hata tam buydu.)
        while (i < s.Length && (s[i] == ' ' || s[i] == '\t' || s[i] == '\n' || s[i] == '\r')) i++;
        int j = i;
        while (j < s.Length && (char.IsDigit(s[j]) || s[j] == '-' || s[j] == '.' || s[j] == '+' || s[j] == 'e' || s[j] == 'E')) j++;
        float v;
        float.TryParse(s.Substring(i, j - i).Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out v);
        return v;
    }

    public static void Run(string gtaFolder, string mloName, string partName, string cellsJson, string outJson)
    {
        var cells = ReadCells(cellsJson);
        Console.WriteLine("[*] yerel hucre: {0}", cells.Count);
        if (cells.Count == 0) { Console.WriteLine("[!] hucre okunamadi"); return; }

        uint mloHash  = Joaat(mloName);
        uint partHash = Joaat(partName);

        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        // 1) MLO archetype icinde PARCA'nin yerel yerlesimi
        Vector3 partPos = Vector3.Zero;
        Quaternion partRot = Quaternion.Identity;
        bool partFound = false;

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
                    var m = a as MloArchetype;
                    if (m == null || m.entities == null) continue;
                    if (m._BaseArchetypeDef.name.Hash != mloHash) continue;
                    foreach (var me2 in m.entities)
                    {
                        var d = me2.Data;
                        if (d.archetypeName.Hash != partHash) continue;
                        partPos = d.position;
                        partRot = new Quaternion(d.rotation.X, d.rotation.Y, d.rotation.Z, d.rotation.W);
                        partFound = true;
                        break;
                    }
                }
                if (partFound) break;
            }
            if (partFound) break;
        }

        if (!partFound) { Console.WriteLine("[!] {0} MLO'sunda {1} bulunamadi", mloName, partName); return; }
        Console.WriteLine("[*] parca yerel konum: ({0:0.000}, {1:0.000}, {2:0.000})", partPos.X, partPos.Y, partPos.Z);
        Console.WriteLine("[*] parca rotasyon (ham): ({0:0.####}, {1:0.####}, {2:0.####}, {3:0.####}) uzunluk={4:0.####}",
            partRot.X, partRot.Y, partRot.Z, partRot.W, partRot.Length());

        // DEJENERE QUATERNION KORUMASI.
        // Bazi entity'lerde rotasyon (0,0,0,0) olarak duruyor. Bununla
        // Vector3.Transform SIFIR vektor dondurur ve tum noktalar tek yere
        // coker (ilk denemede 233 hucrenin hepsi ayni koordinata dustu).
        // Uzunlugu ~0 olan quaternion'u birim kabul ediyoruz.
        partRot = SafeQuat(partRot, "parca");

        // 2) MLO'nun dunya yerlesimleri (ayni MLO birden fazla yerde olabilir)
        var seen = new HashSet<string>();
        var sb = new StringBuilder();
        sb.Append("{\n \"mlo\": \"").Append(mloName).Append("\",\n \"part\": \"").Append(partName).Append("\",\n \"sites\": [\n");
        int siteCount = 0;

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
                var mis = y.CMloInstanceDefs;
                if (mis == null) continue;

                foreach (var mi in mis)
                {
                    var ced = mi.CEntityDef;
                    if (ced.archetypeName.Hash != mloHash) continue;

                    var mloPos = ced.position;
                    var mloRot = SafeQuat(new Quaternion(ced.rotation.X, ced.rotation.Y, ced.rotation.Z, ced.rotation.W), "mlo");

                    string key = string.Format(CultureInfo.InvariantCulture, "{0:0.00}_{1:0.00}_{2:0.00}", mloPos.X, mloPos.Y, mloPos.Z);
                    if (!seen.Add(key)) continue;

                    if (siteCount > 0) sb.Append(",\n");
                    sb.Append("  { \"origin\": [")
                      .Append(F(mloPos.X)).Append(", ").Append(F(mloPos.Y)).Append(", ").Append(F(mloPos.Z))
                      .Append("], \"ymap\": \"").Append(fe.Name).Append("\",\n    \"cells\": [\n");

                    for (int i = 0; i < cells.Count; i++)
                    {
                        var c = cells[i];
                        // panelLocal -> mloLocal
                        var pl = new Vector3(c.X, c.Y, c.Z);
                        var mlocal = partPos + Vector3.Transform(pl, partRot);
                        // mloLocal -> world
                        var w = mloPos + Vector3.Transform(mlocal, mloRot);
                        // dis normal de ayni donusumlerden gecer (yon, konum degil)
                        var nl = new Vector3(c.NX, c.NY, 0f);
                        var nw = Vector3.Transform(Vector3.Transform(nl, partRot), mloRot);
                        double head = Math.Atan2(nw.Y, nw.X) * 180.0 / Math.PI;

                        if (i > 0) sb.Append(",\n");
                        sb.Append("     { \"p\": [").Append(F(w.X)).Append(", ").Append(F(w.Y)).Append(", ").Append(F(w.Z))
                          .Append("], \"h\": ").Append(F((float)head)).Append(" }");
                    }
                    sb.Append("\n    ]\n  }");
                    siteCount++;
                }
            }
        }

        sb.Append("\n ]\n}\n");
        File.WriteAllText(outJson, sb.ToString(), new UTF8Encoding(false));
        Console.WriteLine("[+] {0} sube x {1} hucre -> {2}", siteCount, cells.Count, outJson);
    }

    static string F(float v) { return v.ToString("0.####", CultureInfo.InvariantCulture); }

    static bool warned;
    static Quaternion SafeQuat(Quaternion q, string what)
    {
        if (q.Length() < 0.001f)
        {
            if (!warned) { Console.WriteLine("[!] {0} rotasyonu dejenere (0,0,0,0) -> birim kabul edildi", what); warned = true; }
            return Quaternion.Identity;
        }
        q.Normalize();
        return q;
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

[MloToWorld]::Run($GtaFolder, $Mlo, $Part, $CellsJson, $OutJson)
