# build_extensions.ps1 - indexes ytyp ARCHETYPE EXTENSIONS.
#
# WHY A SEPARATE INDEX: archetypes.tsv.gz holds one row PER archetype;
# extensions are 0..N per archetype. They do not fit in the same table. Also,
# extensions answer questions of their own:
#
#   "which prop makes dust when it explodes"   -> Particle  (fxType=4)
#   "which props have an expression"           -> Expression (.yed chain)
#   "which prop grows grass around it"         -> ProcObject
#   "does this door have a door extension"     -> Door
#
# Extension TYPES (14, the MCExtensionDef* classes in CodeWalker.Core;
# exactly the same list as Sollumz 2.9 ytyp/properties/extensions.py):
#   ParticleEffect  AudioCollisionSettings  AudioEmitter  ExplosionEffect
#   Ladder  Buoyancy  LightShaft  SpawnPoint  SpawnPointOverride
#   WindDisturbance  ProcObject  Expression  Door  LightEffect
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_extensions.ps1 `
#       [-GtaFolder <path>] [-CodeWalker <CodeWalker.Core.dll>] `
#       [-ExtraFolders @('<server resources path>')] [-Out <data folder>]
#
# NOTE: passing -ExtraFolders to PowerShell with -File breaks the array; a comma
# list becomes ONE STRING. If you need an array use -Command "& script.ps1 -ExtraFolders @(...)".

param(
    [string]   $GtaFolder,
    [string]   $CodeWalker,
    [string[]] $ExtraFolders = @(),
    [string]   $Out
)

$ErrorActionPreference = 'Stop'

if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent) 'data' }
if (-not (Test-Path -LiteralPath $Out)) { New-Item -ItemType Directory -Path $Out | Out-Null }

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker) {
    # Last resort: search the disk. SLOW (scans under C:\). To make it permanent:
    #   python assetdb.py path codewalker "<path>"
    $CodeWalker = Get-ChildItem -Path "$env:USERPROFILE\Desktop","C:\" -Filter 'CodeWalker.Core.dll' `
                    -Recurse -Depth 4 -ErrorAction SilentlyContinue |
                  Select-Object -First 1 -ExpandProperty FullName
}
if (-not $CodeWalker -or -not (Test-Path -LiteralPath $CodeWalker)) {
    throw "CodeWalker.Core.dll not found. Pass it with -CodeWalker <path>."
}

$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder

$cwDir = Split-Path $CodeWalker -Parent
Write-Output "CodeWalker : $CodeWalker"
Write-Output "GTA V      : $(if($GtaFolder){$GtaFolder}else{'(none)'})"
Write-Output "Extra      : $(if($ExtraFolders.Count){$ExtraFolders -join '; '}else{'(none)'})"
Write-Output "Output     : $Out"

# -- Runtime dependency resolution ----------------------------------------
$script:cwDir = $cwDir
[System.AppDomain]::CurrentDomain.add_AssemblyResolve([System.ResolveEventHandler]{
    param($sender, $e)
    $short = ($e.Name -split ',')[0]
    $p = Join-Path $script:cwDir "$short.dll"
    if (Test-Path -LiteralPath $p) { return [System.Reflection.Assembly]::LoadFrom($p) }
    return $null
})

$src = @'
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Text;
using CodeWalker.GameFiles;

public static class ExtensionIndexer
{
    static string F(float v) { return v.ToString("0.####", CultureInfo.InvariantCulture); }

    // In a custom ytyp the archetype name and the Expression's exprDict/expr fields are
    // stored as HASHES; CodeWalker resolves them only if they are in JenkIndex.
    //
    // MEASURED: this step was MISSING in the first version and the 5 Expressions of
    // my_depobox.ytyp came out as '2590473487' -- the asset was fine, the index was blind.
    // '.yed' is fed too because the Expression extension takes the dictionary name from it.
    static void SeedNames(string folder, ref int seeded)
    {
        string[] exts = { "*.ydr", "*.yft", "*.ydd", "*.ytd", "*.yed", "*.ycd", "*.ybn" };
        foreach (var ext in exts)
        {
            string[] files;
            try { files = Directory.GetFiles(folder, ext, SearchOption.AllDirectories); }
            catch { continue; }
            foreach (var f in files)
            {
                var n = Path.GetFileNameWithoutExtension(f);
                if (string.IsNullOrEmpty(n)) continue;
                JenkIndex.Ensure(n.ToLowerInvariant());
                seeded++;
            }
        }
    }

    // NOTE: do not make SharpDX.Vector3 a PARAMETER type. Add-Type then requires an
    // mscorlib reference (CS0012 'ValueType'). That is also why build_archetypes.ps1
    // uses the fields inline.
    static string V3(float x, float y, float z) { return F(x) + "," + F(y) + "," + F(z); }

    static string H(MetaHash h)
    {
        // MetaHash.ToString() gives the name if it can be resolved, otherwise the hash.
        var s = h.ToString();
        return string.IsNullOrEmpty(s) ? "0" : s;
    }

    static string Clean(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        return s.Replace('\t', ' ').Replace('\n', ' ').Replace('\r', ' ');
    }

    // Columns: archetype src ytyp extType extName offsetPos
    //          fxName fxType boneTag scale probability extFlags detay
    // 'detay' (Turkish for "detail") stays as the column name: assetdb.py reads the column by it.
    static void Row(StringBuilder sb, string arch, string src, string ytyp,
                    string type, string name, string pos,
                    string fxName, string fxType, string boneTag,
                    string scale, string prob, string flags, string detail)
    {
        sb.Append(Clean(arch)).Append('\t')
          .Append(src).Append('\t')
          .Append(Clean(ytyp)).Append('\t')
          .Append(type).Append('\t')
          .Append(Clean(name)).Append('\t')
          .Append(pos).Append('\t')
          .Append(Clean(fxName)).Append('\t')
          .Append(fxType).Append('\t')
          .Append(boneTag).Append('\t')
          .Append(scale).Append('\t')
          .Append(prob).Append('\t')
          .Append(flags).Append('\t')
          .Append(Clean(detail)).Append('\n');
    }

    static void Emit(StringBuilder sb, Archetype a, string src, string ytyp, ref int n)
    {
        if (a == null || a.Extensions == null) return;

        foreach (var w in a.Extensions)
        {
            if (w == null) continue;
            string arch = a.Name;

            var pe = w as MCExtensionDefParticleEffect;
            if (pe != null)
            {
                var d = pe.Data;
                Row(sb, arch, src, ytyp, "Particle", H(d.name), V3(d.offsetPosition.X, d.offsetPosition.Y, d.offsetPosition.Z),
                    pe.fxName, d.fxType.ToString(), d.boneTag.ToString(),
                    F(d.scale), d.probability.ToString(), d.flags.ToString(),
                    "color=0x" + d.color.ToString("X8"));
                n++; continue;
            }

            var ex = w as MCExtensionDefExpression;
            if (ex != null)
            {
                var d = ex.Data;
                Row(sb, arch, src, ytyp, "Expression", H(d.name), V3(d.offsetPosition.X, d.offsetPosition.Y, d.offsetPosition.Z),
                    "", "", "", "", "", "",
                    "exprDict=" + H(d.expressionDictionaryName)
                    + ";expr=" + H(d.expressionName)
                    + ";creatureMeta=" + H(d.creatureMetadataName)
                    + ";onCollision=" + d.initialiseOnCollision.ToString());
                n++; continue;
            }

            var po = w as MCExtensionDefProcObject;
            if (po != null)
            {
                var d = po.Data;
                Row(sb, arch, src, ytyp, "ProcObject", H(d.name), V3(d.offsetPosition.X, d.offsetPosition.Y, d.offsetPosition.Z),
                    "", "", "", "", "", d.flags.ToString(),
                    "obj=" + d.objectHash.ToString()
                    + ";rIn=" + F(d.radiusInner) + ";rOut=" + F(d.radiusOuter)
                    + ";spacing=" + F(d.spacing)
                    + ";scale=" + F(d.minScale) + ".." + F(d.maxScale)
                    + ";scaleZ=" + F(d.minScaleZ) + ".." + F(d.maxScaleZ)
                    + ";zOff=" + F(d.minZOffset) + ".." + F(d.maxZOffset));
                n++; continue;
            }

            // The other 11 types: their field schemas differ a lot and are not
            // queried at the moment. Recording that they exist is enough -- "does this archetype
            // have a Ladder/Door/AudioEmitter" is answered that way too.
            var tn = w.GetType().Name;
            if (tn.StartsWith("MCExtensionDef")) tn = tn.Substring("MCExtensionDef".Length);
            Row(sb, arch, src, ytyp, tn, Clean(w.Name), "", "", "", "", "", "", "", "");
            n++;
        }
    }

    public static void Run(string gtaFolder, string codeWalkerDll, string[] extraFolders, string outFolder)
    {
        var sb = new StringBuilder(1 << 22);
        // The last column keeps its Turkish name 'detay': assetdb.py reads it (data/ column, do not rename).
        sb.Append("archetype\tsrc\tytyp\textType\textName\toffsetPos\tfxName\tfxType\tboneTag\tscale\tprobability\textFlags\tdetay\n");

        int vanillaYtyp = 0, customYtyp = 0, nExt = 0, errors = 0;
        var t0 = DateTime.Now;

        if (!string.IsNullOrEmpty(gtaFolder))
        {
            GTA5Keys.LoadFromPath(gtaFolder, null);
            var man = new RpfManager();
            man.Init(gtaFolder, s => { }, s => { }, false, true);

            var entries = new List<RpfFileEntry>();
            foreach (var rpf in man.AllRpfs)
                foreach (var e in rpf.AllEntries)
                {
                    var fe = e as RpfFileEntry;
                    if (fe != null && fe.NameLower.EndsWith(".ytyp")) entries.Add(fe);
                }
            Console.WriteLine("[*] Vanilla ytyp entries: {0}", entries.Count);

            foreach (var e in entries)
            {
                try
                {
                    var data = e.File.ExtractFile(e);
                    if (data == null || data.Length == 0) { errors++; continue; }
                    var y = new YtypFile();
                    y.Load(data, e);
                    vanillaYtyp++;
                    if (y.AllArchetypes == null) continue;
                    foreach (var a in y.AllArchetypes) Emit(sb, a, "vanilla", e.Name, ref nExt);
                }
                catch { errors++; }
            }
            Console.WriteLine("[*] Vanilla: {0} ytyp, {1} extensions", vanillaYtyp, nExt);
        }

        // Names are fed AFTER THE VANILLA SCAN: RpfManager.Init rebuilds
        // JenkIndex and erases anything fed before.
        int seeded = 0;
        foreach (var f in extraFolders)
            if (Directory.Exists(f)) SeedNames(f, ref seeded);
        if (extraFolders.Length > 0)
            Console.WriteLine("[*] Custom names fed to JenkIndex: {0}", seeded);

        foreach (var folder in extraFolders)
        {
            if (!Directory.Exists(folder)) { Console.WriteLine("[!] missing: {0}", folder); continue; }
            string[] files;
            try { files = Directory.GetFiles(folder, "*.ytyp", SearchOption.AllDirectories); }
            catch { continue; }
            foreach (var f in files)
            {
                try
                {
                    var data = File.ReadAllBytes(f);
                    var y = new YtypFile();
                    y.Load(data);
                    customYtyp++;
                    if (y.AllArchetypes == null) continue;
                    foreach (var a in y.AllArchetypes) Emit(sb, a, "custom", Path.GetFileName(f), ref nExt);
                }
                catch { errors++; }
            }
        }
        Console.WriteLine("[*] Custom: {0} ytyp", customYtyp);

        var outPath = Path.Combine(outFolder, "ytyp_extensions.tsv.gz");
        var raw = Encoding.UTF8.GetBytes(sb.ToString());
        using (var fs = File.Create(outPath))
        using (var gz = new GZipStream(fs, CompressionLevel.Optimal))
            gz.Write(raw, 0, raw.Length);

        Console.WriteLine("[+] {0}  ({1:0.0} KB compressed)", outPath, new FileInfo(outPath).Length / 1024.0);
        Console.WriteLine("[+] Total {0} extensions, {1:0.0} s, {2} errors",
                          nExt, (DateTime.Now - t0).TotalSeconds, errors);
    }
}
'@

# 'mscorlib' is REQUIRED: this script passes structs (MetaHash, SharpDX.Vector3) as METHOD
# PARAMETERS; the compiler then looks for the 'ValueType' type and
# crashes with CS0012 without an mscorlib reference. build_archetypes.ps1 does not have this line
# because there the structs are always used inline, never as parameters.
$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'mscorlib',
          'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[ExtensionIndexer]::Run($GtaFolder, $CodeWalker, $ExtraFolders, $Out)
