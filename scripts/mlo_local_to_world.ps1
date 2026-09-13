# mlo_local_to_world.ps1 - converts LOCAL coordinates inside an MLO interior
# into all of its world placements.
#
# WHY: we find a point inside an MLO (e.g. a box cell on the vault wall)
# in Blender, in the model's local space. To use it in the game that point must go
# first through the placement of the PART (drawable entity) inside the interior, then through
# the MLO's world placement. The same MLO can be in several places on the map
# (Fleeca: 6 locations) - it is computed for each one separately.
#
# CHAIN:  panelLocal -> (part pos/rot) -> mloLocal -> (mlo pos/rot) -> world
# The raw quaternion is the right convention; same math as build_entities.ps1
# (verified with v_ilev_gb_teldr @ Legion).
#
# Usage:
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

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) { throw "CodeWalker.Core.dll not found." }
$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V folder not found." }

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

    // A very small JSON reader: the shape of this file is fixed (flat number fields).
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
        // Skip the WHITESPACE after the colon. Without skipping, the scanner stopped at once
        // and returned an empty string -> every field read as 0 -> all cells
        // collapsed onto one point. (That was exactly the bug in the first run.)
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
        Console.WriteLine("[*] local cells: {0}", cells.Count);
        if (cells.Count == 0) { Console.WriteLine("[!] could not read cells"); return; }

        uint mloHash  = Joaat(mloName);
        uint partHash = Joaat(partName);

        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        // 1) Local placement of the PART inside the MLO archetype
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

        if (!partFound) { Console.WriteLine("[!] {1} not found in MLO {0}", mloName, partName); return; }
        Console.WriteLine("[*] part local position: ({0:0.000}, {1:0.000}, {2:0.000})", partPos.X, partPos.Y, partPos.Z);
        Console.WriteLine("[*] part rotation (raw): ({0:0.####}, {1:0.####}, {2:0.####}, {3:0.####}) length={4:0.####}",
            partRot.X, partRot.Y, partRot.Z, partRot.W, partRot.Length());

        // DEGENERATE QUATERNION GUARD.
        // Some entities store the rotation as (0,0,0,0). With that,
        // Vector3.Transform returns a ZERO vector and all points collapse onto one spot
        // (in the first attempt all 233 cells landed on the same coordinate).
        // A quaternion with length ~0 is treated as identity.
        partRot = SafeQuat(partRot, "part");

        // 2) World placements of the MLO (the same MLO can be in several places)
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
                        // the outward normal goes through the same transforms (direction, not position)
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
        Console.WriteLine("[+] {0} sites x {1} cells -> {2}", siteCount, cells.Count, outJson);
    }

    static string F(float v) { return v.ToString("0.####", CultureInfo.InvariantCulture); }

    static bool warned;
    static Quaternion SafeQuat(Quaternion q, string what)
    {
        if (q.Length() < 0.001f)
        {
            if (!warned) { Console.WriteLine("[!] {0} rotation is degenerate (0,0,0,0) -> treated as identity", what); warned = true; }
            return Quaternion.Identity;
        }
        q.Normalize();
        return q;
    }
}
'@

# 'System.Collections'/'System.Runtime'/'System.Console' are REQUIRED: under PowerShell 7 (.NET 8+)
# these types are FORWARDED from netstandard; without a reference
# Add-Type crashes with "CS1069: type has been forwarded" / "CS0103: Console does not exist".
# Windows PowerShell 5.1 has no problem with it; PS7 fails every time.
$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[MloToWorld]::Run($GtaFolder, $Mlo, $Part, $CellsJson, $OutJson)
