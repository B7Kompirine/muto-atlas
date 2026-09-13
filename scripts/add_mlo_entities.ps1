# add_mlo_entities.ps1 - adds new objects to an MLO's ENTITY LIST.
#
# WHY: a prop CANNOT be placed inside an MLO interior from an outside ymap - the
# room/portal system culls it (measured). Spawning it from a script does not make
# a map object either (the door system cannot find it, fragment collision does not
# follow the animation), and on a 60-player server every client carries its own spawn load.
# The right way: write the object into the MLO's OWN list. Then the MLO places
# the object, the server carries no load, and it appears in every place the MLO
# exists on the map (Fleeca: 6 locations) at once.
#
# COORDINATES: the entity position must be in MLO-LOCAL space. If the cell data is in
# the local space of a PART (drawable), the chain is:
#     panelLocal -> (part pos/rot) -> mloLocal
# This script does that transform; it does NOT need world coordinates.
#
# Usage:
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
    # ROOM NAME - TREAT IT AS REQUIRED. If an MLO entity is NOT LISTED in a
    # room's AttachedObjects list, the game NEVER CREATES it
    # and reports no error. Adding it to the entities array alone is NOT ENOUGH.
    [string] $Room = '',
    [int]    $Count = 20,
    # Defaults for an MLO INTERIOR entity. If you put standalone ymap
    # values here (flags=1572872, ORPHANHD) the object
    # SILENTLY DOES NOT APPEAR - the ytyp loads, the entity shows in the list, but
    # nothing appears in the game. Vanilla MLO entities use 18350080
    # (measured from v_genbank).
    [uint32] $Flags = 18350080,
    [single] $LodDist = -1,
    # Push the box out from the wall (m). 0 = on the texture plane.
    [single] $Offset = 0.0,
    [string] $GtaFolder,
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker) { throw "CodeWalker.Core.dll not found." }
$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V folder not found." }

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
        // Skip the WHITESPACE after the colon - if it is not skipped every value
        // reads as 0 and all cells collapse onto one point.
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
        Console.WriteLine("[*] local cells: {0}", cells.Count);
        if (cells.Count == 0) { Console.WriteLine("[!] could not read cells"); return; }

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
        if (found == null) { Console.WriteLine("[!] {0} not found", ytypName); return; }

        // PATCHES MUST STACK.
        // If every run reads from the vanilla RPF we OVERWRITE the previous patch.
        // (Real case: a door swap was made, then adding boxes to the same ytyp
        // turned the doors back to vanilla.) If the file exists in the output
        // folder we continue FROM IT.
        var existing = Path.Combine(outDir, ytypName);
        var y = new YtypFile();
        if (File.Exists(existing))
        {
            y.Load(File.ReadAllBytes(existing));
            Console.WriteLine("[*] continuing from the existing patched file: {0}", existing);
        }
        else
        {
            y.Load(found.File.ExtractFile(found), found);
            Console.WriteLine("[*] read from the vanilla source");
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
        if (target == null) { Console.WriteLine("[!] MLO {0} not found", mloName); return; }

        // THE PART MAY NOT BE IN THE TARGET MLO.
        // The same interior can have two versions (v_genbank and
        // hei_generic_bank_dlc) and both share THE SAME MLO-local frame -
        // the same prop sits at the same local position in both.
        // If the reference part is not in the target we search ALL ytyps.
        if (partPos == Vector3.Zero)
        {
            Console.WriteLine("[*] part '{0}' is not in this MLO - searching other MLOs", partName);
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
                            Console.WriteLine("[*] part found in {0}", fe2.Name);
                            got = true; break;
                        }
                        if (got) break;
                    }
                    if (got) break;
                }
                if (got) break;
            }
            if (!got) { Console.WriteLine("[!] part {0} not found anywhere", partName); return; }
        }

        int before = target.entities.Length;
        Console.WriteLine("[*] MLO {0}: existing entities = {1}", mloName, before);
        Console.WriteLine("[*] part local: ({0:0.###}, {1:0.###}, {2:0.###})", partPos.X, partPos.Y, partPos.Z);

        // Pick cells at EVEN SPACING - so they do not all bunch up in one corner
        int step = Math.Max(1, cells.Count / Math.Max(1, count));
        var picked = new List<Cell>();
        for (int i = 0; i < cells.Count && picked.Count < count; i += step) picked.Add(cells[i]);

        var list = new List<MCEntityDef>(target.entities);
        foreach (var c in picked)
        {
            // panelLocal -> mloLocal
            var pl = new Vector3(c.X + c.NX * offset, c.Y + c.NY * offset, c.Z);
            var mlocal = partPos + Vector3.Transform(pl, partRot);

            // Outward-facing wall normal -> entity heading (around Z)
            var nl = Vector3.Transform(new Vector3(c.NX, c.NY, 0f), partRot);
            double head = Math.Atan2(nl.Y, nl.X);
            var rot = Quaternion.RotationAxis(Vector3.UnitZ, (float)head);

            var ed = new CEntityDef();
            ed.archetypeName = new MetaHash(modelHash);
            ed.position = mlocal;
            // MLO entity rotation is stored INVERTED (conjugate)
            ed.rotation = new Vector4(-rot.X, -rot.Y, -rot.Z, rot.W);
            ed.scaleXY = 1.0f; ed.scaleZ = 1.0f;
            ed.parentIndex = -1;
            ed.lodDist = lodDist; ed.childLodDist = 0;
            ed.lodLevel = rage__eLodType.LODTYPES_DEPTH_ORPHANHD;
            ed.priorityLevel = rage__ePriorityLevel.PRI_REQUIRED;
            ed.flags = flags;
            ed.ambientOcclusionMultiplier = 255;
            ed.artificialAmbientOcclusion = 255;

            // MCEntityDef has NO parameterless constructor.
            // ctor(ref CEntityDef, MloArchetype) is used.
            list.Add(new MCEntityDef(ref ed, target));
        }

        int firstNew = target.entities.Length;
        target.entities = list.ToArray();
        Console.WriteLine("[+] {0} entities added -> total {1}", picked.Count, target.entities.Length);

        // -- ATTACH TO ROOM ----------------------------------------------
        // If this step is skipped the object SILENTLY does not appear: the ytyp loads, the entity
        // shows in the list, nothing appears in the game. (Measured.)
        if (!string.IsNullOrEmpty(room) && target.rooms != null)
        {
            MCMloRoomDef rd = null;
            foreach (var r in target.rooms)
                if (string.Equals(r.RoomName, room, StringComparison.OrdinalIgnoreCase)) { rd = r; break; }

            if (rd == null)
            {
                Console.WriteLine("[X] room '{0}' not found. Existing rooms:", room);
                foreach (var r in target.rooms) Console.WriteLine("      {0}", r.RoomName);
                return;
            }

            var ao = new List<uint>(rd.AttachedObjects ?? new uint[0]);
            int had = ao.Count;
            for (int i = 0; i < picked.Count; i++) ao.Add((uint)(firstNew + i));
            rd.AttachedObjects = ao.ToArray();
            Console.WriteLine("[+] room '{0}': attachedObjects {1} -> {2}", rd.RoomName, had, ao.Count);
        }
        else
        {
            Console.WriteLine("[!] -Room not given - the entities are attached to NO ROOM and are INVISIBLE in the game.");
        }

        var outPath = Path.Combine(outDir, ytypName);
        var bytes = y.Save();
        File.WriteAllBytes(outPath, bytes);

        // READ BACK AND VERIFY
        var chk = new YtypFile();
        chk.Load(File.ReadAllBytes(outPath));
        int n = 0, mine = 0;
        foreach (var a in chk.AllArchetypes) {
            var m = a as MloArchetype;
            if (m == null || m.entities == null || m._BaseArchetypeDef.name.Hash != mloHash) continue;
            n = m.entities.Length;
            foreach (var me in m.entities) if (me.Data.archetypeName.Hash == modelHash) mine++;
        }
        Console.WriteLine("[+] written: {0} ({1:N0} bytes)", outPath, bytes.Length);
        Console.WriteLine(n == before + picked.Count && mine == picked.Count
            ? string.Format("[+] verification OK: entities {0} -> {1}, '{2}' = {3} instances", before, n, model, mine)
            : string.Format("[X] VERIFICATION FAILED: expected {0}, read {1} ('{2}' {3})", before + picked.Count, n, model, mine));
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

[MloEntityAdder]::Run($GtaFolder, $YtypName, $Mlo, $Part, $Model, $CellsJson, $OutDir, $Count, $LodDist, $Offset, $Flags, $Room)
