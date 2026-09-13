# build_usage.ps1 — vanilla modellerin GERCEKTE kullandigi shader ve collision
# materyallerini indeksler.
#
# NEDEN: shaders.tsv (249) ve collision_materials.tsv (185) tablolarini
# Sollumz'un kendi dosyalarindan cikardik. Ikisi de TEK KAYNAK. Bugune kadarki
# guclu dogrulamalarimiz hep IKI BAGIMSIZ KAYNAGIN kesismesinden geldi
# ('Has Anim' biti <-> clipDict, specialAttribute <-> door physics,
# ANIMAL_DEFAULT <-> eski olcumumuz). Bu iki tabloda o kesisim yoktu.
#
# Bu betik ikinci kaynagi uretir: oyunun kendi .ydr/.yft/.ybn dosyalari.
# Ayni anda uc soruyu cevaplar:
#   1) shaders.tsv'deki adlar gercekten kullaniliyor mu, eksik var mi
#   2) collision_materials.tsv indeksleri dogru araliktaki degerlerle
#      ortusuyor mu
#   3) DECAL shader'lari hangi RenderBucket ile kullaniliyor
#      (Sollumz varsayilani Opaque(0); dogrusu ne, ancak boyle olculur)
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_usage.ps1
#       [-Limit 4000]   # taranacak dosya sayisi (0 = hepsi, yavas)

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
    throw "CodeWalker.Core.dll bulunamadi."
}
$GtaFolder = & "$PSScriptRoot\paths.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V klasoru bulunamadi." }

$cwDir = Split-Path $CodeWalker -Parent
Write-Output "CodeWalker : $CodeWalker"
Write-Output "GTA V      : $GtaFolder"
Write-Output "Limit      : $(if($Limit -gt 0){$Limit}else{'(hepsi)'})"

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
    // shader adi -> (renderBucket -> adet)
    static Dictionary<string, Dictionary<int, int>> shaderUse =
        new Dictionary<string, Dictionary<int, int>>();
    // collision materyal indeksi -> adet
    static Dictionary<int, int> matUse = new Dictionary<int, int>();
    // materyal indeksi -> gorulen proceduralId'ler
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

    // NOT: Drawable ile FragDrawable AYRI tiplerdir (ortak taban yok), o yuzden
    // fonksiyon ShaderGroup aliyor -- ikisi de onu veriyor.
    // !! ResourcePointerArray64<T> uzerinde foreach KULLANMA.
    // IEnumerable uyguluyor gorunuyor ama GetEnumerator() ->
    // NotImplementedException. Derleyici sikayet etmez, calisma aninda her
    // dosya sessizce hataya duser (ilk surumde 86.690 ydr'nin HEPSI boyle
    // kayboldu). Dogru erisim: .data_items dizisi.
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

    // Bounds agaci: composite -> children -> ... ; her dugumde materyal olabilir
    static void WalkBounds(Bounds b, int derinlik)
    {
        if (b == null || derinlik > 8) return;

        var geom = b as BoundGeometry;
        if (geom != null && geom.Materials != null)
        {
            foreach (var m in geom.Materials)
                AddMat((int)m.Type, m.ProceduralId);
        }
        else
        {
            // primitive bound (box/cylinder/sphere/capsule): tek materyal indeksi
            AddMat(b.MaterialIndex, 0);
        }

        var comp = b as BoundComposite;
        if (comp != null && comp.Children != null)
        {
            var ch = comp.Children.data_items;   // foreach DEGIL, bkz. yukarisi
            if (ch != null)
                for (int i = 0; i < ch.Length; i++) WalkBounds(ch[i], derinlik + 1);
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
        // Sessiz yutma tuzagi: ilk surumde tum ydr'ler hata verdi ve
        // 'ydr tarandi: 0' disinda hicbir bilgi yoktu. Ilk hatayi yazdir.
        string ilkHata = null;

        int denenenD = 0;
        foreach (var fe in ydr)
        {
            // DENENEN sayilir, BASARILI degil: hepsi hata verirse limit
            // hic devreye girmez ve 86.690 dosya taranir.
            if (limit > 0 && denenenD >= limit) break;
            denenenD++;
            try
            {
                var data = fe.File.ExtractFile(fe);
                if (data == null || data.Length == 0) { err++; continue; }
                var f = new YdrFile(); f.Load(data, fe);
                if (f.Drawable != null) WalkShaderGroup(f.Drawable.ShaderGroup);
                nD++;
            }
            catch (Exception ex) { err++; if (ilkHata == null) ilkHata = fe.Name + " -> " + ex.GetType().Name + ": " + ex.Message; }
        }
        Console.WriteLine("[*] ydr tarandi: {0}", nD);
        if (ilkHata != null) Console.WriteLine("[!] ilk ydr hatasi: {0}", ilkHata);

        int denenenF = 0;
        foreach (var fe in yft)
        {
            if (limit > 0 && denenenF >= limit) break;
            denenenF++;
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
        Console.WriteLine("[*] yft tarandi: {0}", nF);

        int denenenB = 0;
        foreach (var fe in ybn)
        {
            if (limit > 0 && denenenB >= limit) break;
            denenenB++;
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
        Console.WriteLine("[*] ybn tarandi: {0}", nB);

        // ---- shader kullanimi ----
        var sb = new StringBuilder();
        sb.Append("shader\ttotal\tbuckets\n");
        foreach (var kv in shaderUse)
        {
            int toplam = 0;
            var parts = new List<string>();
            foreach (var b in kv.Value) toplam += b.Value;
            foreach (var b in kv.Value) parts.Add(b.Key + ":" + b.Value);
            sb.Append(kv.Key).Append('\t').Append(toplam).Append('\t')
              .Append(string.Join(";", parts.ToArray())).Append('\n');
        }
        var utf8NoBom = new UTF8Encoding(false);   // Encoding.UTF8 BOM yazar; ilk sutun adi bozulur
        File.WriteAllText(Path.Combine(outFolder, "shader_usage.tsv"), sb.ToString(), utf8NoBom);

        // ---- collision materyal kullanimi ----
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

        Console.WriteLine("[+] shader_usage.tsv    ({0} farkli shader)", shaderUse.Count);
        Console.WriteLine("[+] collision_usage.tsv ({0} farkli materyal indeksi)", matUse.Count);
        Console.WriteLine("[+] {0:0.0} sn, {1} hata", (DateTime.Now - t0).TotalSeconds, err);
    }
}
'@

$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'mscorlib', 'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console',
          'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[UsageIndexer]::Run($GtaFolder, $Out, $Limit)
