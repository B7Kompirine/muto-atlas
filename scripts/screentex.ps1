# screentex.ps1 - reads a model's SHADER/TEXTURE mapping from the RPFs.
#
# WHY: drawing a DUI onto a prop's screen needs AddReplaceTexture(origTxd,
# origTxn, ...). origTxd = texture dictionary name, origTxn = the texture name
# IN THAT DICTIONARY. These two CANNOT BE GUESSED:
#   - the prop name and the txd name are usually NOT THE SAME
#   - a prop has 5-10 textures; which one is the screen is not obvious
# That is why cr-3dnui_laptopdemo tries a list of 10 candidates and cycles through them
# one by one with /lapnext. That is guessing; the query below gives the answer directly.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File screentex.ps1 -Model prop_laptop_lester
#   powershell -NoProfile -ExecutionPolicy Bypass -File screentex.ps1 -Model prop_tv_flat_01 -All
#
# -All   : print ALL texture parameters, not only diffuse (normal/spec included)
# -Deep  : for external (not embedded) textures, open ALL .ytd files and find which
#          dictionary they are in. SLOW (minutes). The screen texture is usually
#          embedded in the model, so this is mostly NOT NEEDED.
# -TxdHash <number> : the textureDict value from the assetdb.py show output; converts the hash
#          to a .ytd name (for information - it is NOT the screen texture's dictionary).
#
# Output fields:
#   embedded : the texture is INSIDE the model (the drawable's own TextureDictionary).
#              Then origTxd = the MODEL NAME; there is no separate .ytd.
#   <ytd>    : the texture is in an external dictionary. origTxd = the name of that .ytd (no extension).

param(
    [Parameter(Mandatory=$true)][string] $Model,
    [switch]   $All,
    [switch]   $Deep,
    [string]   $TxdHash,
    [string]   $GtaFolder,
    [string]   $CodeWalker
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
using System.IO;
using CodeWalker.GameFiles;

public static class ScreenTex
{
    public static void Run(string gtaFolder, string model, bool all, bool deep, string txdHash)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        model = model.Trim().ToLowerInvariant();

        // 1) Find the model's drawable file (.ydr / .yft / .ydd, in that order).
        RpfFileEntry drawableEntry = null;
        string drawableExt = null;

        // 2) In the same pass hash every .ytd name -> so we can go from a hash back to the name.
        //    This is the only way to find which dictionary a texture is in.
        var ytdByHash = new Dictionary<uint, string>();
        var ytdEntries = new List<RpfFileEntry>();

        foreach (var rpf in man.AllRpfs)
        {
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null) continue;
                var nl = fe.NameLower ?? "";

                if (nl.EndsWith(".ytd"))
                {
                    var shortName = nl.Substring(0, nl.Length - 4);
                    uint h = JenkHash.GenHash(shortName);
                    if (!ytdByHash.ContainsKey(h)) ytdByHash[h] = shortName;
                    ytdEntries.Add(fe);
                    continue;
                }

                if (drawableEntry != null) continue;
                if (nl == model + ".ydr")      { drawableEntry = fe; drawableExt = "ydr"; }
                else if (nl == model + ".yft") { drawableEntry = fe; drawableExt = "yft"; }
                else if (nl == model + ".ydd") { drawableEntry = fe; drawableExt = "ydd"; }
            }
        }

        if (drawableEntry == null)
        {
            Console.WriteLine("[!] no .ydr/.yft/.ydd found for '{0}'. Is the name right?", model);
            return;
        }

        Console.WriteLine("[=] {0}.{1}   (rpf: {2})", model, drawableExt, drawableEntry.Path);

        // Print the ytyp textureDict hash if it can be resolved. CAREFUL: measured that this
        // field is NOT the dictionary the screen texture is in (prop_monitor_01a:
        // ytyp textureDict=3126464848, while the screen texture is EMBEDDED in the model).
        if (!string.IsNullOrWhiteSpace(txdHash))
        {
            uint th;
            if (uint.TryParse(txdHash.Trim(), out th))
            {
                string tn;
                Console.WriteLine("[i] ytyp textureDict {0} -> {1}", th,
                    ytdByHash.TryGetValue(th, out tn) ? tn + ".ytd" : "(no .ytd with this name in the RPFs)");
            }
        }

        var data = drawableEntry.File.ExtractFile(drawableEntry);
        var drawables = new List<KeyValuePair<string, DrawableBase>>();

        if (drawableExt == "ydr")
        {
            var f = RpfFile.GetFile<YdrFile>(drawableEntry, data);
            if (f != null && f.Drawable != null) drawables.Add(new KeyValuePair<string, DrawableBase>(model, f.Drawable));
        }
        else if (drawableExt == "yft")
        {
            var f = RpfFile.GetFile<YftFile>(drawableEntry, data);
            if (f != null && f.Fragment != null && f.Fragment.Drawable != null)
                drawables.Add(new KeyValuePair<string, DrawableBase>(model, f.Fragment.Drawable));
        }
        else
        {
            var f = RpfFile.GetFile<YddFile>(drawableEntry, data);
            if (f != null && f.Drawables != null)
                for (int i = 0; i < f.Drawables.Length; i++)
                    drawables.Add(new KeyValuePair<string, DrawableBase>(f.Drawables[i].Name ?? ("drawable" + i), f.Drawables[i]));
        }

        if (drawables.Count == 0) { Console.WriteLine("[!] Could not read the drawable."); return; }

        foreach (var kv in drawables)
        {
            var d = kv.Value;
            if (d.ShaderGroup == null || d.ShaderGroup.Shaders == null) continue;

            // Texture dictionary embedded INSIDE the model (if any). If embedded, origTxd = the model name.
            var embedded = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var etd = d.ShaderGroup.TextureDictionary;
            if (etd != null && etd.Textures != null && etd.Textures.data_items != null)
                foreach (var t in etd.Textures.data_items)
                    if (t != null && t.Name != null) embedded.Add(t.Name);

            Console.WriteLine("");
            Console.WriteLine("--- drawable: {0}   shader count: {1}   embedded textures: {2}",
                kv.Key, d.ShaderGroup.Shaders.data_items.Length, embedded.Count);

            int si = 0;
            foreach (var sh in d.ShaderGroup.Shaders.data_items)
            {
                si++;
                if (sh == null || sh.ParametersList == null || sh.ParametersList.Parameters == null) continue;

                var pars = sh.ParametersList.Parameters;
                var hashes = sh.ParametersList.Hashes;

                for (int i = 0; i < pars.Length; i++)
                {
                    var p = pars[i];
                    if (p == null || p.DataType != 0) continue;      // 0 = texture
                    var tex = p.Data as TextureBase;
                    if (tex == null || string.IsNullOrEmpty(tex.Name)) continue;

                    string pname = (hashes != null && i < hashes.Length) ? hashes[i].ToString() : ("param" + i);
                    bool isDiffuse = pname.IndexOf("Diffuse", StringComparison.OrdinalIgnoreCase) >= 0;
                    if (!all && !isDiffuse) continue;

                    string where;
                    if (embedded.Contains(tex.Name))
                    {
                        where = "embedded -> origTxd = " + model;
                    }
                    else
                    {
                        // External texture: inside which .ytd? Scan the candidates.
                        if (!deep) { where = "EXTERNAL texture -> run the ytd scan with -Deep"; }
                        else
                        {
                            var owner = FindYtd(man, ytdEntries, tex.Name);
                            where = owner != null ? ("ytd: " + owner) : "?? (not found)";
                        }
                    }

                    Console.WriteLine("  shader#{0,-2} {1,-16} sh={2,-24} txn='{3}'   {4}",
                        si, pname, sh.Name.ToString(), tex.Name, where);
                }
            }
        }
    }

    // Find the .ytd that contains a texture name. First try the dictionaries with a similar
    // name (cheap); if not found, open all of them (expensive but certain).
    static Dictionary<string, string> _ytdCache = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

    static string FindYtd(RpfManager man, List<RpfFileEntry> ytds, string texName)
    {
        string cached;
        if (_ytdCache.TryGetValue(texName, out cached)) return cached;

        foreach (var fe in ytds)
        {
            try
            {
                var d = fe.File.ExtractFile(fe);
                if (d == null || d.Length == 0) continue;
                var ytd = RpfFile.GetFile<YtdFile>(fe, d);
                if (ytd == null || ytd.TextureDict == null || ytd.TextureDict.Textures == null) continue;
                var items = ytd.TextureDict.Textures.data_items;
                if (items == null) continue;
                foreach (var t in items)
                {
                    if (t != null && string.Equals(t.Name, texName, StringComparison.OrdinalIgnoreCase))
                    {
                        var nl = fe.NameLower;
                        var shortName = nl.Substring(0, nl.Length - 4);
                        _ytdCache[texName] = shortName;
                        return shortName;
                    }
                }
            }
            catch { }
        }
        _ytdCache[texName] = null;
        return null;
    }
}
'@

$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'),
          'netstandard', 'System.Collections', 'System.Runtime', 'System.Linq',
          'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[ScreenTex]::Run($GtaFolder, $Model, $All.IsPresent, $Deep.IsPresent, $TxdHash)
