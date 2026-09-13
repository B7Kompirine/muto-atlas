# build_usage.ps1 - indexes the shaders and collision materials that vanilla models
# REALLY use.
#
# WHY: we extracted the shaders.tsv (249) and collision_materials.tsv (185) tables
# from Sollumz's own files. Both are a SINGLE SOURCE. Our strongest verifications
# so far have always come from the intersection of TWO INDEPENDENT SOURCES
# ('Has Anim' bit <-> clipDict, specialAttribute <-> door physics,
# ANIMAL_DEFAULT <-> our earlier measurement). These two tables had no such intersection.
#
# This script produces the second source: the game's own .ydr/.yft/.ybn files.
# It answers three questions at once:
#   1) are the names in shaders.tsv really used, is any missing
#   2) do the collision_materials.tsv indexes match values in the
#      right range
#   3) which RenderBucket DECAL shaders are used with
#      (the Sollumz default is Opaque(0); what is right can only be measured this way)
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_usage.ps1
#       [-Limit 4000]   # number of files to scan (0 = all, slow)

param(
    [string] $GtaFolder,
    [string] $CodeWalker,
    [string] $Out,
    [int]    $Limit = 6000
)

$ErrorActionPreference = 'Stop'

if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent) 'data' }
if (-not (Test-Path -LiteralPath $Out)) { New-Item -ItemType Directory -Path $Out | Out-Null }

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path -LiteralPath $CodeWalker)) {
    throw "CodeWalker.Core.dll not found."
}
$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V folder not found." }

$cwDir = Split-Path $CodeWalker -Parent
Write-Output "CodeWalker : $CodeWalker"
Write-Output "GTA V      : $GtaFolder"
Write-Output "Limit      : $(if($Limit -gt 0){$Limit}else{'(all)'})"

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
using System.Text;
using CodeWalker.GameFiles;

public static class UsageIndexer
{
    // shader name -> (renderBucket -> count)
    static Dictionary<string, Dictionary<int, int>> shaderUse =
        new Dictionary<string, Dictionary<int, int>>();
    // collision material index -> count
    static Dictionary<int, int> matUse = new Dictionary<int, int>();
    // material index -> proceduralIds seen
    static Dictionary<int, HashSet<int>> matProc = new Dictionary<int, HashSet<int>>();

    static void AddShader(string name, int bucket)
    {
        if (string.IsNullOrEmpty(name)) return;
        Dictionary<int, int> d;
        if (!shaderUse.TryGetValue(name, out d)) { d = new Dictionary<int, int>(); shaderUse[name] = d; }
        int c; d.TryGetValue(bucket, out c); d[bucket] = c + 1;
    }

    static void AddMat(int idx, int procId)
    {
        int c; matUse.TryGetValue(idx, out c); matUse[idx] = c + 1;
        if (procId > 0)
        {
            HashSet<int> s;
            if (!matProc.TryGetValue(idx, out s)) { s = new HashSet<int>(); matProc[idx] = s; }
            s.Add(procId);
        }
    }

    // NOTE: Drawable and FragDrawable are SEPARATE types (no common base), so
    // the function takes a ShaderGroup -- both provide one.
    // !! Do NOT USE foreach on ResourcePointerArray64<T>.
    // It appears to implement IEnumerable, but GetEnumerator() ->
    // NotImplementedException. The compiler does not complain; at run time every
    // file silently fails (in the first version ALL 86,690 ydr files were
    // lost this way). The right access: the .data_items array.
    static void WalkShaderGroup(ShaderGroup sg)
    {
        if (sg == null || sg.Shaders == null) return;
        var arr = sg.Shaders.data_items;
        if (arr == null) return;
        for (int i = 0; i < arr.Length; i++)
        {
            var s = arr[i];
            if (s == null) continue;
            AddShader(s.Name.ToString(), s.RenderBucket);
        }
    }

    // Bounds tree: composite -> children -> ... ; any node can have a material
    static void WalkBounds(Bounds b, int depth)
    {
        if (b == null || depth > 8) return;

        var geom = b as BoundGeometry;
        if (geom != null && geom.Materials != null)
        {
            foreach (var m in geom.Materials)
                AddMat((int)m.Type, m.ProceduralId);
        }
        else
        {
            // primitive bound (box/cylinder/sphere/capsule): a single material index
            AddMat(b.MaterialIndex, 0);
        }

        var comp = b as BoundComposite;
        if (comp != null && comp.Children != null)
        {
            var ch = comp.Children.data_items;   // NOT foreach, see above
            if (ch != null)
                for (int i = 0; i < ch.Length; i++) WalkBounds(ch[i], depth + 1);
        }
    }

    public static void Run(string gtaFolder, string outFolder, int limit)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        var ydr = new List<RpfFileEntry>();
        var yft = new List<RpfFileEntry>();
        var ybn = new List<RpfFileEntry>();
        foreach (var rpf in man.AllRpfs)
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null) continue;
                if (fe.NameLower.EndsWith(".ydr")) ydr.Add(fe);
                else if (fe.NameLower.EndsWith(".yft")) yft.Add(fe);
                else if (fe.NameLower.EndsWith(".ybn")) ybn.Add(fe);
            }
        Console.WriteLine("[*] ydr={0} yft={1} ybn={2}", ydr.Count, yft.Count, ybn.Count);

        var t0 = DateTime.Now;
        int nD = 0, nF = 0, nB = 0, err = 0;
        // Silent swallowing pitfall: in the first version every ydr failed and
        // there was no information except 'ydr scanned: 0'. Print the first error.
        string firstError = null;

        int triedD = 0;
        foreach (var fe in ydr)
        {
            // Count ATTEMPTS, not SUCCESSES: if all of them fail the limit
            // never kicks in and 86,690 files get scanned.
            if (limit > 0 && triedD >= limit) break;
            triedD++;
            try
            {
                var data = fe.File.ExtractFile(fe);
                if (data == null || data.Length == 0) { err++; continue; }
                var f = new YdrFile(); f.Load(data, fe);
                if (f.Drawable != null) WalkShaderGroup(f.Drawable.ShaderGroup);
                nD++;
            }
            catch (Exception ex) { err++; if (firstError == null) firstError = fe.Name + " -> " + ex.GetType().Name + ": " + ex.Message; }
        }
        Console.WriteLine("[*] ydr scanned: {0}", nD);
        if (firstError != null) Console.WriteLine("[!] first ydr error: {0}", firstError);

        int triedF = 0;
        foreach (var fe in yft)
        {
            if (limit > 0 && triedF >= limit) break;
            triedF++;
            try
            {
                var data = fe.File.ExtractFile(fe);
                if (data == null || data.Length == 0) { err++; continue; }
                var f = new YftFile(); f.Load(data, fe);
                if (f.Fragment != null && f.Fragment.Drawable != null)
                    WalkShaderGroup(f.Fragment.Drawable.ShaderGroup);
                nF++;
            }
            catch { err++; }
        }
        Console.WriteLine("[*] yft scanned: {0}", nF);

        int triedB = 0;
        foreach (var fe in ybn)
        {
            if (limit > 0 && triedB >= limit) break;
            triedB++;
            try
            {
                var data = fe.File.ExtractFile(fe);
                if (data == null || data.Length == 0) { err++; continue; }
                var f = new YbnFile(); f.Load(data, fe);
                WalkBounds(f.Bounds, 0);
                nB++;
            }
            catch { err++; }
        }
        Console.WriteLine("[*] ybn scanned: {0}", nB);

        // ---- shader usage ----
        var sb = new StringBuilder();
        sb.Append("shader\ttotal\tbuckets\n");
        foreach (var kv in shaderUse)
        {
            int total = 0;
            var parts = new List<string>();
            foreach (var b in kv.Value) total += b.Value;
            foreach (var b in kv.Value) parts.Add(b.Key + ":" + b.Value);
            sb.Append(kv.Key).Append('\t').Append(total).Append('\t')
              .Append(string.Join(";", parts.ToArray())).Append('\n');
        }
        var utf8NoBom = new UTF8Encoding(false);   // Encoding.UTF8 writes a BOM; the first column name breaks
        File.WriteAllText(Path.Combine(outFolder, "shader_usage.tsv"), sb.ToString(), utf8NoBom);

        // ---- collision material usage ----
        var sb2 = new StringBuilder();
        sb2.Append("matIndex\tcount\tproceduralIds\n");
        foreach (var kv in matUse)
        {
            string procs = "";
            HashSet<int> s;
            if (matProc.TryGetValue(kv.Key, out s))
            {
                var l = new List<string>();
                foreach (var p in s) l.Add(p.ToString());
                l.Sort();
                procs = string.Join(",", l.ToArray());
            }
            sb2.Append(kv.Key).Append('\t').Append(kv.Value).Append('\t').Append(procs).Append('\n');
        }
        File.WriteAllText(Path.Combine(outFolder, "collision_usage.tsv"), sb2.ToString(), utf8NoBom);

        Console.WriteLine("[+] shader_usage.tsv    ({0} distinct shaders)", shaderUse.Count);
        Console.WriteLine("[+] collision_usage.tsv ({0} distinct material indexes)", matUse.Count);
        Console.WriteLine("[+] {0:0.0} s, {1} errors", (DateTime.Now - t0).TotalSeconds, err);
    }
}
'@

$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'mscorlib', 'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console',
          'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[UsageIndexer]::Run($GtaFolder, $Out, $Limit)
