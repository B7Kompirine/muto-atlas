# clip_bones.ps1 — bir klibin hedeflediği KEMIK TAG'lerini cikarir.
#
# NEDEN: klip kac kemik animasyonluyor bilmek yetmez; HANGI kemikleri
# hedefledigi gerekir. O tag listesi, klibi oynatabilecek modeli kesin
# olarak belirler (assetdb.py clipfit bu ciktiyi iskelet indeksiyle esler).
#
# Kullanim:
#   powershell -File clip_bones.ps1 -Dict <anim@dict> -Clip <klip> [-Json]

param(
    [Parameter(Mandatory=$true)][string] $Dict,
    [Parameter(Mandatory=$true)][string] $Clip,
    [string] $GtaFolder,
    [string] $CodeWalker,
    [switch] $Json
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

public static class ClipBones
{
    static void Collect(Animation a, List<ushort> outTags)
    {
        if (a == null) return;
        try
        {
            var ids = a.BoneIds;
            var items = ids.data_items;
            if (items == null) return;
            foreach (var b in items) outTags.Add(b.BoneId);
        }
        catch { }
    }

    public static void Run(string gtaFolder, string dictName, string clipName, bool json)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        string want = dictName.ToLowerInvariant() + ".ycd";
        foreach (var rpf in man.AllRpfs)
        {
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null || fe.NameLower != want) continue;
                byte[] data;
                try { data = fe.File.ExtractFile(fe); } catch { continue; }
                if (data == null || data.Length == 0) continue;

                var y = new YcdFile();
                try { y.Load(data, fe); } catch { continue; }
                if (y.ClipMapEntries == null) continue;

                foreach (var cme in y.ClipMapEntries)
                {
                    if (cme == null || cme.Clip == null) continue;
                    string nm = null;
                    try { nm = cme.Clip.ShortName; } catch { }
                    if (nm == null || !nm.Equals(clipName, StringComparison.OrdinalIgnoreCase)) continue;

                    var tags = new List<ushort>();
                    var ca = cme.Clip as ClipAnimation;
                    if (ca != null) Collect(ca.Animation, tags);
                    var cl = cme.Clip as ClipAnimationList;
                    if (cl != null)
                        foreach (var ce in cl.Animations) { if (ce != null) Collect(ce.Animation, tags); }

                    var uniq = new List<ushort>();
                    var seen = new HashSet<ushort>();
                    foreach (var t in tags) if (seen.Add(t)) uniq.Add(t);

                    if (json)
                    {
                        Console.Write("{\"dict\":\"" + dictName + "\",\"clip\":\"" + nm + "\",\"tags\":[");
                        for (int i = 0; i < uniq.Count; i++) { if (i > 0) Console.Write(","); Console.Write(uniq[i]); }
                        Console.WriteLine("]}");
                    }
                    else
                    {
                        Console.WriteLine("dict : {0}", dictName);
                        Console.WriteLine("clip : {0}", nm);
                        Console.WriteLine("tag  : {0} adet", uniq.Count);
                        Console.WriteLine(string.Join(",", uniq));
                    }
                    return;
                }
            }
        }
        Console.WriteLine(json ? "{\"error\":\"bulunamadi\"}" : "BULUNAMADI: " + dictName + " / " + clipName);
    }
}
'@

# 'System.Collections'/'System.Runtime'/'System.Console' SART: PowerShell 7 (.NET 8+)
# altinda bu tipler netstandard'dan FORWARD edilmis durumda; referans verilmezse
# Add-Type "CS1069: type has been forwarded" / "CS0103: Console does not exist"
# ile coker. Windows PowerShell 5.1'de sorun cikmaz, PS7'de her seferinde cikar.
$refs = @($CodeWalker, (Join-Path $cwDir 'SharpDX.dll'), (Join-Path $cwDir 'SharpDX.Mathematics.dll'), 'netstandard',
          'System.Collections', 'System.Runtime', 'System.Linq', 'System.Console', 'System.IO.Compression', 'System.Text.RegularExpressions')
Add-Type -TypeDefinition $src -ReferencedAssemblies $refs -Language CSharp

[ClipBones]::Run($GtaFolder, $Dict, $Clip, $Json.IsPresent)
