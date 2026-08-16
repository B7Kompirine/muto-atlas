# build_pedrig.ps1 — ped iskeletlerinin REST POSE'unu data/pedrig.json'a yazar.
#
# NEDEN: skeletons.tsv.gz kemik ADI/TAG/PARENT tutar ama TRANSFORM tutmaz.
# Rigging icin rest pose sart:
#   • kemigin uzunluk ekseni LOCAL +X'tir  -> translation = [uzunluk,0,0]
#   • SKEL_Pelvis / SKEL_Spine_Root rest'te +-90 Y cevirici, eklem degil
#   • ayna simetrisi Z isaretidir
#   • .ycd fcurve degerleri MUTLAK kemik-yerel yonelimdir; gercek eklem
#     acisi 2*acos(|dot(q_klip,q_rest)|) — yani q_rest olmadan hesaplanamaz.
#
# Kullanim:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_pedrig.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -Command "& build_pedrig.ps1 -Peds @('mp_m_freemode_01','player_zero')"

param(
    [string[]] $Peds = @('mp_m_freemode_01','mp_f_freemode_01','player_zero','player_one','player_two'),
    [string]   $GtaFolder,
    [string]   $CodeWalker,
    [string]   $Out
)

$ErrorActionPreference = 'Stop'

if (-not $Out) { $Out = Join-Path (Split-Path $PSScriptRoot -Parent) 'data' }
if (-not (Test-Path $Out)) { New-Item -ItemType Directory -Path $Out -Force | Out-Null }

$CodeWalker = & "$PSScriptRoot\yol.ps1" codewalker $CodeWalker
if (-not $CodeWalker -or -not (Test-Path $CodeWalker)) { throw "CodeWalker.Core.dll bulunamadi." }

$GtaFolder = & "$PSScriptRoot\yol.ps1" gta $GtaFolder
if (-not $GtaFolder) { throw "GTA V klasoru bulunamadi. -GtaFolder <yol> ile ver." }

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
using System.Text;
using CodeWalker.GameFiles;

public static class PedRigBuilder
{
    static string F(float v) { return v.ToString("R", CultureInfo.InvariantCulture); }

    public static void Run(string gtaFolder, string[] peds, string outFolder)
    {
        GTA5Keys.LoadFromPath(gtaFolder, null);
        var man = new RpfManager();
        man.Init(gtaFolder, s => { }, s => { }, false, true);

        var want = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var p in peds) want.Add(p.Trim() + ".yft");

        var done = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var sb = new StringBuilder();
        sb.Append("{\n \"peds\": {\n");
        bool firstPed = true;

        foreach (var rpf in man.AllRpfs)
        {
            foreach (var e in rpf.AllEntries)
            {
                var fe = e as RpfFileEntry;
                if (fe == null || !want.Contains(fe.Name) || done.Contains(fe.Name)) continue;

                byte[] data;
                try { data = fe.File.ExtractFile(fe); }
                catch (Exception ex) { Console.WriteLine("[!] {0}: {1}", fe.Name, ex.Message); continue; }
                if (data == null || data.Length == 0) continue;

                YftFile yft;
                try
                {
                    var rrfe = fe as RpfResourceFileEntry;
                    if (rrfe != null)
                    {
                        data = ResourceBuilder.Compress(data);
                        data = ResourceBuilder.AddResourceHeader(rrfe, data);
                    }
                    yft = RpfFile.GetResourceFile<YftFile>(data);
                }
                catch (Exception ex) { Console.WriteLine("[!] {0}: okunamadi ({1})", fe.Name, ex.Message); continue; }

                // DIKKAT: Add-Type'in C# 5 derleyicisi `?.` bilmez -> acik null kontrolu.
                Skeleton skel = null;
                if (yft != null && yft.Fragment != null && yft.Fragment.Drawable != null)
                    skel = yft.Fragment.Drawable.Skeleton;
                if (skel == null || skel.Bones == null || skel.Bones.Items == null)
                {
                    Console.WriteLine("[!] {0}: iskelet yok", fe.Name); continue;
                }

                done.Add(fe.Name);
                var name = Path.GetFileNameWithoutExtension(fe.Name);
                if (!firstPed) sb.Append(",\n");
                firstPed = false;
                sb.Append("  \"").Append(name).Append("\": [\n");

                var bones = skel.Bones.Items;
                for (int i = 0; i < bones.Length; i++)
                {
                    var b = bones[i];
                    if (i > 0) sb.Append(",\n");
                    sb.Append("   {\"i\":").Append(i)
                      .Append(",\"n\":\"").Append(b.Name).Append("\"")
                      .Append(",\"tag\":").Append(b.Tag)
                      .Append(",\"p\":").Append(b.ParentIndex)
                      .Append(",\"t\":[").Append(F(b.Translation.X)).Append(",").Append(F(b.Translation.Y)).Append(",").Append(F(b.Translation.Z)).Append("]")
                      .Append(",\"r\":[").Append(F(b.Rotation.X)).Append(",").Append(F(b.Rotation.Y)).Append(",").Append(F(b.Rotation.Z)).Append(",").Append(F(b.Rotation.W)).Append("]")
                      .Append(",\"s\":[").Append(F(b.Scale.X)).Append(",").Append(F(b.Scale.Y)).Append(",").Append(F(b.Scale.Z)).Append("]}");
                }
                sb.Append("\n  ]");
                Console.WriteLine("[+] {0,-24} {1} kemik", name, bones.Length);
            }
        }

        sb.Append("\n }\n}\n");
        var dst = Path.Combine(outFolder, "pedrig.json");
        File.WriteAllText(dst, sb.ToString());
        Console.WriteLine("[=] yazildi: {0} ({1} ped)", dst, done.Count);

        foreach (var w in want)
            if (!done.Contains(w)) Console.WriteLine("[!] bulunamadi: {0}", w);
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

[PedRigBuilder]::Run($GtaFolder, $Peds, $Out)
