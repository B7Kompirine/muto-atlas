# screentex.ps1 — bir modelin SHADER/DOKU eslesmesini RPF'ten okur.
#
# NEDEN: DUI'yi bir prop'un ekranina basmak icin AddReplaceTexture(origTxd,
# origTxn, ...) gerekir. origTxd = texture dictionary adi, origTxn = O
# SOZLUKTEKI doku adi. Bu ikisi TAHMIN EDILEMEZ:
#   - prop adi ile txd adi cogu zaman AYNI DEGILDIR
#   - bir prop'ta 5-10 doku olur; ekran olan hangisi belli degildir
# cr-3dnui_laptopdemo bu yuzden 10 adaylik bir liste deneyip /lapnext ile
# tek tek cevirir. Bu tahmindir; asagidaki sorgu cevabi dogrudan verir.
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File screentex.ps1 -Model prop_laptop_lester
#   powershell -NoProfile -ExecutionPolicy Bypass -File screentex.ps1 -Model prop_tv_flat_01 -All
#
# -All   : sadece diffuse degil TUM doku parametrelerini yaz (normal/spec dahil)
# -Deep  : harici (gomulu olmayan) dokular icin TUM .ytd'leri acip hangi
#          sozlukte olduklarini bul. YAVAS (dakikalar). Ekran dokusu genelde
#          modele gomulu oldugu icin cogu zaman GEREKMEZ.
# -TxdHash <sayi> : assetdb.py show ciktisindaki textureDict degeri; hash'ten
#          .ytd adina cevirir (bilgi amacli — ekran dokusunun sozlugu DEGIL).
#
# Cikti alanlari:
#   embedded : doku modelin ICINDE (drawable'in kendi TextureDictionary'si).
#              Bu durumda origTxd = MODEL ADI'dir, ayri bir .ytd yoktur.
#   <ytd>    : doku harici bir sozlukte. origTxd = o .ytd'nin adi (uzantisiz).

param(
    [Parameter(Mandatory=$true)][string] $Model,
    [switch]   $All,
    [switch]   $Deep,
    [string]   $TxdHash,
    [string]   $GtaFolder,
    [string]   $CodeWalker
)

$ErrorActionPreference = 'Stop'

$CodeWalker = & "$PSScriptRoot\yol.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) { throw "CodeWalker.Core.dll bulunamadi." }

$GtaFolder = & "$PSScriptRoot\yol.ps1" gta $GtaFolder
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

        // 1) Modelin drawable dosyasini bul (.ydr / .yft / .ydd sirasiyla).
        RpfFileEntry drawableEntry = null;
        string drawableExt = null;

        // 2) Ayni gecmiste tum .ytd adlarini hash'le -> hash'ten ada donebilmek icin.
        //    Bir dokunun hangi sozlukte oldugunu bulmanin tek yolu budur.
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
            Console.WriteLine("[!] '{0}' icin .ydr/.yft/.ydd bulunamadi. Ad dogru mu?", model);
            return;
        }

        Console.WriteLine("[=] {0}.{1}   (rpf: {2})", model, drawableExt, drawableEntry.Path);

        // ytyp'deki textureDict hash'i cozulebiliyorsa yaz. DIKKAT: olculdu ki bu
        // alan ekran dokusunun bulundugu sozluk DEGILDIR (prop_monitor_01a:
        // ytyp textureDict=3126464848, ekran dokusu ise modele GOMULU).
        if (!string.IsNullOrWhiteSpace(txdHash))
        {
            uint th;
            if (uint.TryParse(txdHash.Trim(), out th))
            {
                string tn;
                Console.WriteLine("[i] ytyp textureDict {0} -> {1}", th,
                    ytdByHash.TryGetValue(th, out tn) ? tn + ".ytd" : "(RPF'lerde bu adda .ytd yok)");
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

        if (drawables.Count == 0) { Console.WriteLine("[!] Drawable okunamadi."); return; }

        foreach (var kv in drawables)
        {
            var d = kv.Value;
            if (d.ShaderGroup == null || d.ShaderGroup.Shaders == null) continue;

            // Modelin ICINE gomulu doku sozlugu (varsa). Gomuluyse origTxd = model adi.
            var embedded = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var etd = d.ShaderGroup.TextureDictionary;
            if (etd != null && etd.Textures != null && etd.Textures.data_items != null)
                foreach (var t in etd.Textures.data_items)
                    if (t != null && t.Name != null) embedded.Add(t.Name);

            Console.WriteLine("");
            Console.WriteLine("--- drawable: {0}   shader sayisi: {1}   gomulu doku: {2}",
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
                        // Harici doku: hangi .ytd icinde? Adaylari tara.
                        if (!deep) { where = "HARICI doku -> -Deep ile ytd taramasi yap"; }
                        else
                        {
                            var owner = FindYtd(man, ytdEntries, tex.Name);
                            where = owner != null ? ("ytd: " + owner) : "?? (bulunamadi)";
                        }
                    }

                    Console.WriteLine("  shader#{0,-2} {1,-16} sh={2,-24} txn='{3}'   {4}",
                        si, pname, sh.Name.ToString(), tex.Name, where);
                }
            }
        }
    }

    // Bir doku adini iceren .ytd'yi bul. Once ad benzerligi olan sozlukleri
    // dene (ucuz), bulunamazsa hepsini ac (pahali ama kesin).
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
