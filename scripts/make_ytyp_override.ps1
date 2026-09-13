# make_ytyp_override.ps1 - copies a vanilla archetype, changes ONE field
# and builds an override .ytyp.
#
# WHY: if a prop/door is defined wrong (e.g. an object that should be a door has
# specialAttribute=0) the only right fix is to correct it at ytyp level.
# This script reads the source from the RPF, copies the fields EXACTLY and changes only
# the requested value - no invented fields.
#
# Usage:
#   powershell -File make_ytyp_override.ps1 `
#       -Models v_ilev_gb_teldr,v_ilev_gb_vauldr `
#       -SpecialAttribute 7 `
#       -YtypName my_fleeca_doors `
#       -OutFile "<...>\stream\my_fleeca_doors.ytyp"

param(
    [Parameter(Mandatory=$true)][string[]] $Models,
    [int]    $SpecialAttribute = 7,
    [Parameter(Mandatory=$true)][string] $YtypName,
    [Parameter(Mandatory=$true)][string] $OutFile,
    # Build a new archetype under OUR OWN NAME instead of OVERRIDING the vanilla archetype.
    # The override path (same name) conflicts with the definition the game has already
    # registered and does not hold; a new name is added without conflict. The model file must
    # also be exported under this name.
    [string] $RenameTo,
    # In a custom prop the texture/collision is embedded in the .ydr -> dictionaries 0.
    [switch] $ClearDicts,
    # A .yft (fragment) needs ASSET_TYPE_FRAGMENT; a .ydr needs ASSET_TYPE_DRAWABLE.
    # If the source archetype is a drawable and we built a fragment, CHANGING this is required,
    # otherwise the game loads the model as a drawable and per-bone collision does not kick in.
    [ValidateSet('ASSET_TYPE_UNINITIALIZED','ASSET_TYPE_FRAGMENT','ASSET_TYPE_DRAWABLE',
                 'ASSET_TYPE_DRAWABLEDICTIONARY','ASSET_TYPE_ASSETLESS')]
    [string] $AssetType,
    # In fragments physicsDictionary points to the model's OWN name (not 0).
    # A working reference fragment is like this; applied after ClearDicts.
    [switch] $PhysicsDictSelf,
    [uint32] $Flags = 0,
    [single] $LodDist = 0,
    # Clip dictionary name (BARE name, no extension). Required for animated props.
    [string] $ClipDict,
    # Expression extension: binds the .yed file to the archetype.
    # Give the BARE NAME - the game adds "pack:/" and ".expr" itself.
    # If you write "pack:/x.expr" the expression NEVER loads, but the mesh animation
    # keeps working; the mistake is very hard to notice.
    [string] $Expression,
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
                Console.WriteLine("[!] NOT FOUND: {0}", kv.Value);
        if (found.Count == 0) { Console.WriteLine("[!] No archetype found, exiting."); return; }

        var outYtyp = new YtypFile();
        outYtyp.Name = ytypName;
        outYtyp.NameHash = Joaat(ytypName);
        var mt = outYtyp.CMapTypes;   // struct; copy, modify, write back directly
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
                def.assetName = nh;      // must match the .ydr file name
            }
            if (clearDicts)
            {
                // Texture and collision are embedded in the .ydr -> no external dictionary
                def.physicsDictionary = new MetaHash(0);
                def.textureDictionary = new MetaHash(0);
            }
            if (physicsDictSelf)
            {
                // Fragment: physicsDictionary points to its own name
                def.physicsDictionary = new MetaHash(Joaat(outName));
            }
            if (!string.IsNullOrEmpty(assetType))
            {
                // assetType is a PROPERTY (not a field); its type is rage__fwArchetypeDef__eAssetType.
                def.assetType = (rage__fwArchetypeDef__eAssetType)
                    Enum.Parse(typeof(rage__fwArchetypeDef__eAssetType), assetType);
            }
            if (!string.IsNullOrEmpty(clipDict))
                def.clipDictionary = new MetaHash(Joaat(clipDict));
            if (flags != 0) def.flags = flags;
            if (lodDist > 0) def.lodDist = lodDist;

            var na = outYtyp.AddArchetype();
            na.Init(outYtyp, ref def);

            // -- EXPRESSION EXTENSION ------------------------------------
            // Binds the .yed to the archetype. Collision following the animation
            // works through this binding; without the extension the mesh moves and the collision stays put.
            if (!string.IsNullOrEmpty(expression))
            {
                // Data is a read-only property; we write to the underlying _Data FIELD.
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

            Console.WriteLine("[+] {0,-22} -> {1,-18} specialAttribute {2} -> {3}   (source: {4})",
                want[kv.Key], outName, before, specialAttr, srcYtyp[kv.Key]);
            Console.WriteLine("      bbMin={0}  bbMax={1}  flags={2}  physics={3}  assetType={4}  lodDist={5}",
                def.bbMin, def.bbMax, def.flags, def.physicsDictionary, def.assetType, def.lodDist);
        }

        byte[] outBytes = outYtyp.Save();
        File.WriteAllBytes(outFile, outBytes);
        Console.WriteLine("[+] written: {0}  ({1} bytes, {2} archetypes)", outFile, outBytes.Length, found.Count);
        Console.WriteLine("[i] ytyp name: {0}  (hash {1})", ytypName, Joaat(ytypName));
    }
}
'@

# 'System.Collections'/'System.Runtime'/'System.Console' are REQUIRED: under PowerShell 7 (.NET 8+)
# these types are FORWARDED from netstandard; without a reference
# Add-Type crashes with "CS1069: type has been forwarded" / "CS0103: Console does not exist".
# Windows PowerShell 5.1 has no problem with it; PS7 fails every time.
$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard', 'mscorlib',
          'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[YtypOverride]::Run($GtaFolder, $Models, $SpecialAttribute, $YtypName, $OutFile,
                    $RenameTo, $ClearDicts.IsPresent, $Flags, $LodDist,
                    $AssetType, $PhysicsDictSelf.IsPresent, $ClipDict, $Expression)
