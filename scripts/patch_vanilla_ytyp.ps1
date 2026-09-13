# patch_vanilla_ytyp.ps1 - copies a vanilla .ytyp file IN FULL, changes the fields
# of specific archetypes in it and writes it under THE SAME NAME.
#
# WHY THIS IS DIFFERENT FROM make_ytyp_override.ps1:
#   make_ytyp_override.ps1 builds a NEW ytyp (a new archetype under our own name).
#   That path is right for adding our own model, but useless for fixing an object
#   that is ALREADY ON THE MAP: the entity on the map still points to the vanilla
#   archetype. Adding a NEW ytyp under the vanilla name conflicts too - the game has
#   already registered the first definition.
#
#   The path that works: put the vanilla ytyp FILE into stream/ under the same name.
#   FiveM REPLACES the file in the stream folder by matching the name; the game loads our
#   version. That fixes the entity on the map itself -
#   no need to spawn objects, hide them, or register them in the door system by hand.
#   It applies in every place the MLO exists on the map at once.
#
# RISK: the WHOLE file changes. So the source is read exactly from the RPF,
# only the requested fields are written, and after writing the file is READ BACK and
# compared with the source (archetype count, MLO room/portal/entity counts).
# If the comparison fails the file is DELETED - streaming a broken ytyp breaks the MLO
# completely.
#
# Usage:
#   powershell -File patch_vanilla_ytyp.ps1 `
#       -YtypName int_lev_des.ytyp `
#       -Patch "v_ilev_gb_teldr=specialAttribute:7" `
#       -OutDir "<...>\stream"

param(
    [Parameter(Mandatory=$true)][string]   $YtypName,
    # In the form "archetypeName=field:value", several separated by commas.
    # Supported fields: specialAttribute, flags, lodDist
    [string[]] $Patch = @(),
    # "oldModel=newModel" - changes the model name in the MLO's ENTITY list.
    #
    # WHY IT IS NEEDED: a prop cannot be placed inside an MLO interior from an outside ymap; the
    # room/portal system culls it. The only right way to replace an interior object with our own
    # model is to fix the MLO's own entity list.
    # Then the MLO ITSELF places the object: no hiding, no ymap, no spawn,
    # and it applies in every place the MLO exists on the map at once.
    [string[]] $SwapEntity = @(),
    [Parameter(Mandatory=$true)][string]   $OutDir,
    [string] $GtaFolder,
    [string] $CodeWalker
)

$ErrorActionPreference = 'Stop'

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) { throw "CodeWalker.Core.dll not found." }

$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V folder not found." }

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

    // Builds a signature of the MLO by counting its internal structure. If this signature
    // changed after the round trip, the record is broken.
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

        // Parse the requested changes: "name=field:value"
        var want = new Dictionary<uint, List<KeyValuePair<string,string>>>();
        var names = new Dictionary<uint, string>();
        foreach (var p in patches)
        {
            var eq = p.IndexOf('=');
            if (eq < 0) { Console.WriteLine("[!] could not parse: {0}", p); continue; }
            var archName = p.Substring(0, eq).Trim();
            var rest = p.Substring(eq + 1).Trim();
            var co = rest.IndexOf(':');
            if (co < 0) { Console.WriteLine("[!] could not parse: {0}", p); continue; }
            uint h = Joaat(archName);
            names[h] = archName;
            if (!want.ContainsKey(h)) want[h] = new List<KeyValuePair<string,string>>();
            want[h].Add(new KeyValuePair<string,string>(rest.Substring(0, co).Trim(),
                                                       rest.Substring(co + 1).Trim()));
        }

        // Find the source file in the RPFs
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
        if (found == null) { Console.WriteLine("[!] {0} not found in the RPFs.", ytypName); return; }

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
        string sigBefore = Signature(y);
        Console.WriteLine("[*] source   : {0}", found.Path);
        Console.WriteLine("[*] signature: {0}", sigBefore);

        // Change the fields. The ELEMENTS of AllArchetypes return structs;
        // to make the change stick it has to be written back to the archetype
        // object with Init.
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
                        Console.WriteLine("[!] unsupported field: {0}", kv.Key);
                        break;
                }
            }
            a.Init(y, ref def);
            changed++;
        }

        // -- MLO ENTITY MODEL SWAP ---------------------------------------
        var swapMap = new Dictionary<uint, KeyValuePair<string,string>>();
        foreach (var s in swaps)
        {
            var eq = s.IndexOf('=');
            if (eq < 0) { Console.WriteLine("[!] could not parse: {0}", s); continue; }
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
                    // MCEntityDef.Data returns a STRUCT; copy, modify, write back
                    d.archetypeName = new MetaHash(Joaat(sw.Value));
                    me.Data = d;
                    swapped++;
                    Console.WriteLine("[+] MLO {0}: entity {1} -> {2}  (pos {3})",
                        m._BaseArchetypeDef.name, sw.Key, sw.Value, d.position);
                }
            }
            changed += swapped;
        }

        if (changed == 0) { Console.WriteLine("[!] no change made - file not written."); return; }

        var outPath = Path.Combine(outDir, ytypName);
        var outBytes = y.Save();
        File.WriteAllBytes(outPath, outBytes);

        // ---- READ BACK AND VERIFY ----
        var check = new YtypFile();
        check.Load(File.ReadAllBytes(outPath));
        string sigAfter = Signature(check);
        Console.WriteLine("[*] written signature: {0}", sigAfter);

        bool ok = (sigBefore == sigAfter);
        if (ok)
        {
            foreach (var a in check.AllArchetypes)
            {
                var def = a._BaseArchetypeDef;
                if (want.ContainsKey(def.name.Hash))
                    Console.WriteLine("    verify: {0} specialAttribute={1} flags={2} lodDist={3}",
                        names[def.name.Hash], def.specialAttribute, def.flags, def.lodDist);
            }
            // Did the model swap really reach the file?
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
                Console.WriteLine("    verify: new model in {0} entities, old model left in {1} entities", seen, leftover);
                if (seen != swapped || leftover != 0) ok = false;
            }
        }

        if (!ok)
        {
            File.Delete(outPath);
            Console.WriteLine("[X] SIGNATURE MISMATCH - file DELETED. Streaming a broken ytyp breaks the MLO.");
            return;
        }

        Console.WriteLine("[+] written: {0}  ({1} bytes, {2} archetypes changed)", outPath, outBytes.Length, changed);
        Console.WriteLine("[i] add it to fxmanifest ONLY as files{{}} - do NOT add data_file DLC_ITYP_REQUEST.");
        Console.WriteLine("    This is a vanilla file REPLACEMENT, not a new ityp registration.");
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

[YtypPatcher]::Run($GtaFolder, $YtypName, $Patch, $OutDir, $SwapEntity)
