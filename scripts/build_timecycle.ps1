# build_timecycle.ps1 — GTA V TIMECYCLE MODIFIER KATALOGU.
#
# NEDEN: bir prop'un ic mekanda neden koyu gorundugu genellikle prop'ta degil,
# odanin TIMECYCLE MODIFIER'indadir. Oda `timecycleName` ile bir modifier'a
# baglanir; o modifier ortam isigini, sis yogunlugunu, pozlamayi ezer. Isigi
# dogru kurup hala "karanlik" goruyorsan sebebi burasidir -- ve bu dosyaya
# bakmadan tahmin edilemez.
#
# ONEMLI: ayni dosya adi (timecycle_mods_1.xml) BIRDEN COK DLC rpf'sinde
# bulunur. extract_asset.ps1 ile ada gore cikarmak SESSIZCE ust uste yazar
# (12 dosyadan 4'u kalir). Bu yuzden burada RPF'ler kendimiz gezilir ve her
# satir HANGI RPF'ten geldigiyle birlikte yazilir. Ayni modifier'i birden cok
# DLC tanimliyorsa ikisi de kayda gecer; hangisinin kazandigi DLC yukleme
# sirasina baglidir ve bu dosyadan OKUNAMAZ -- o yuzden gizlenmez, gosterilir.
#
# XML YAPISI:
#   <timecycle_modifier_data>
#     <modifier name="li" numMods="32" userFlags="0">
#       <light_dir_col_r>0.886 0.000</light_dir_col_r>   <- value1 value2
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_timecycle.ps1

param(
    [string] $GtaFolder,
    [string] $CodeWalker,
    [string] $Out
)

$ErrorActionPreference = 'Stop'

if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent) 'data' }
if (-not (Test-Path -LiteralPath $Out)) { New-Item -ItemType Directory -Path $Out | Out-Null }

$CodeWalker = & "$PSScriptRoot\paths.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path -LiteralPath $CodeWalker)) { throw "CodeWalker.Core.dll bulunamadi." }
$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V klasoru bulunamadi." }

$cwDir = Split-Path $CodeWalker -Parent
Write-Output "CodeWalker : $CodeWalker"
Write-Output "GTA V      : $GtaFolder"

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
using System.Xml;
using CodeWalker.GameFiles;

public static class TimecycleIndexer
{
    static string Clean(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        return s.Replace('\t', ' ').Replace('\n', ' ').Replace('\r', ' ').Trim();
    }

    public static void Run(string gtaFolder, string outFolder)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        var dosyalar = new List<RpfFileEntry>();
        foreach (var rpf in man.AllRpfs)
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null) continue;
                var n = fe.NameLower;
                if (n.StartsWith("timecycle_mods") && n.EndsWith(".xml")) dosyalar.Add(fe);
            }
        Console.WriteLine("[*] timecycle_mods dosyasi: {0}", dosyalar.Count);

        var t0 = DateTime.Now;
        var sb = new StringBuilder(1 << 22);
        sb.Append("modifier\tparam\tvalue1\tvalue2\tnumMods\tsource\n");

        var modAd = new Dictionary<string, int>();      // ad -> kac kaynakta tanimli
        int nSatir = 0, hata = 0;
        string ilkHata = null;

        foreach (var fe in dosyalar)
        {
            try
            {
                var data = fe.File.ExtractFile(fe);
                if (data == null || data.Length == 0) { hata++; continue; }
                var metin = Encoding.UTF8.GetString(data);
                var doc = new XmlDocument();
                doc.LoadXml(metin);

                // Kaynak = iceren rpf'in yolu; ayni dosya adi birden cok DLC'de var.
                string kaynak = fe.File.Path + "/" + fe.Name;

                var mods = doc.SelectNodes("//modifier");
                foreach (XmlNode m in mods)
                {
                    var adAttr = m.Attributes["name"];
                    if (adAttr == null) continue;
                    string ad = Clean(adAttr.Value);
                    if (ad.Length == 0) continue;
                    string numMods = "";
                    var nmAttr = m.Attributes["numMods"];
                    if (nmAttr != null) numMods = nmAttr.Value;

                    if (modAd.ContainsKey(ad)) modAd[ad] = modAd[ad] + 1; else modAd[ad] = 1;

                    foreach (XmlNode p in m.ChildNodes)
                    {
                        if (p.NodeType != XmlNodeType.Element) continue;
                        var parca = Clean(p.InnerText).Split(new char[] { ' ', '\t' },
                                                             StringSplitOptions.RemoveEmptyEntries);
                        string v1 = (parca.Length > 0) ? parca[0] : "";
                        string v2 = (parca.Length > 1) ? parca[1] : "";
                        sb.Append(ad).Append('\t')
                          .Append(Clean(p.Name)).Append('\t')
                          .Append(v1).Append('\t').Append(v2).Append('\t')
                          .Append(numMods).Append('\t')
                          .Append(Clean(kaynak)).Append('\n');
                        nSatir++;
                    }
                }
            }
            catch (Exception ex)
            {
                hata++;
                if (ilkHata == null) ilkHata = fe.Name + ": " + ex.Message;
            }
        }

        Console.WriteLine("[*] okunan dosya: {0}, hata: {1}", dosyalar.Count - hata, hata);
        if (ilkHata != null) Console.WriteLine("[!] ilk hata: {0}", ilkHata);

        int cokKaynakli = 0;
        foreach (var kv in modAd) if (kv.Value > 1) cokKaynakli++;

        var outPath = Path.Combine(outFolder, "timecycle.tsv.gz");
        var raw = Encoding.UTF8.GetBytes(sb.ToString());
        using (var fs = File.Create(outPath))
        using (var gz = new GZipStream(fs, CompressionLevel.Optimal))
            gz.Write(raw, 0, raw.Length);

        Console.WriteLine("[+] timecycle.tsv.gz  ({0} benzersiz modifier / {1} parametre satiri)",
                          modAd.Count, nSatir);
        Console.WriteLine("[+] birden cok kaynakta tanimli modifier: {0}", cokKaynakli);
        Console.WriteLine("[+] {0:0.0} sn", (DateTime.Now - t0).TotalSeconds);
    }
}
'@

$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'mscorlib', 'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console',
          'System.IO.Compression', 'System.Xml', 'System.Xml.ReaderWriter')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[TimecycleIndexer]::Run($GtaFolder, $Out)
