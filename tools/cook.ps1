# cook.ps1 -- drive the Conan Exiles Enhanced Dev Kit to discover/apply/cook the
# ExampleMod mod. Run from PowerShell:
#   D:\MyDev\conan-mod\tools\cook.ps1 -Mode discover
#   D:\MyDev\conan-mod\tools\cook.ps1 -Mode apply
#   D:\MyDev\conan-mod\tools\cook.ps1 -Mode cook
#
# Real install (verified 2026-06-27):
#   DevKit   : C:\Program Files\Epic Games\CEUE5Devkit
#   editor   : <DevKit>\Engine\Binaries\Win64\UnrealEditor-Cmd.exe
#   uproject : <DevKit>\UE4\ConanSandbox.uproject
#   mod dir  : <DevKit>\UE4\Content\Mods\ExampleMod  (already created)
#
# HONEST STATUS: command-line COOK for a single Conan mod is finicky; if -Mode
# cook fails, fall back to the Dev Kit Modding-tab GUI "Cook and Package"
# (cook.ps1 prints the steps). Do NOT assume cook succeeded without seeing the
# .pak on disk. NOTE the DevKit is the 1.3.0 preview; the live server is ~1.2.1
# -- a version-mismatched cook is rejected by the server. Verify before trusting.

param(
    [string] $DevKit = "C:\Program Files\Epic Games\CEUE5Devkit",
    [ValidateSet("discover", "inspect", "dump", "probe", "corefill", "makemc", "findmc", "mcprobe", "exinspect", "relocate", "verify", "override", "apply", "cook")]
    [string] $Mode    = "discover",
    [string] $ModName = "ExampleMod"
)

Clear-Host   # first executable line (param block must precede any statement)
$ErrorActionPreference = "Stop"
Set-Location "D:\MyDev\conan-mod"

if (-not (Test-Path $DevKit)) {
    throw "Dev Kit not found at $DevKit."
}

# ---- locate the toolchain (explicit, with fallbacks) ------------------------
$editor = Join-Path $DevKit "Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
if (-not (Test-Path $editor)) {
    $editor = Get-ChildItem -Path $DevKit -Filter "UnrealEditor-Cmd.exe" -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $editor) { throw "No UnrealEditor-Cmd.exe under $DevKit." }

$uproject = Join-Path $DevKit "UE4\ConanSandbox.uproject"
if (-not (Test-Path $uproject)) {
    $uproject = Get-ChildItem -Path $DevKit -Filter "ConanSandbox.uproject" -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $uproject) { throw "ConanSandbox.uproject not found under $DevKit." }

$pyScript = "D:\MyDev\conan-mod\tools\edit_datatables.py"
$log      = "D:\tmp\conan_$Mode.log"

Write-Host "[cook] editor   : $editor"
Write-Host "[cook] uproject : $uproject"
Write-Host "[cook] mode     : $Mode"
Write-Host "[cook] log      : $log"

# ---- discover / apply -> run the python script inside the editor ------------
if ($Mode -eq "discover" -or $Mode -eq "apply" -or $Mode -eq "inspect" -or $Mode -eq "dump" -or $Mode -eq "probe" -or $Mode -eq "corefill" -or $Mode -eq "makemc" -or $Mode -eq "findmc" -or $Mode -eq "mcprobe" -or $Mode -eq "exinspect" -or $Mode -eq "relocate" -or $Mode -eq "verify" -or $Mode -eq "override") {
    $env:CONAN_MOD_MODE = $Mode
    & $editor "$uproject" -run=pythonscript -script="$pyScript" -unattended -nopause -nosplash -stdout -fullstdoutlogoutput -abslog="$log"
    Write-Host "[cook] python ($Mode) finished. Filter the log for [ExampleMod]:"
    Write-Host "       Select-String -Path '$log' -Pattern '\[ExampleMod\]'"
    return
}

# ---- cook -------------------------------------------------------------------
if ($Mode -eq "cook") {
    & $editor "$uproject" -run=cook -targetplatform=WindowsNoEditor -unattended -nopause -nosplash -stdout -abslog="$log"
    Write-Host ""
    Write-Host "[cook] command-line cook attempted. If no .pak was produced, use the GUI:"
    Write-Host "       1. Launch the Dev Kit from the Epic Launcher Modding tab."
    Write-Host "       2. Open the $ModName mod; File/Modding -> 'Cook and Package' (WindowsNoEditor)."
    Write-Host "       3. Copy the resulting .pak to D:\MyDev\conan-mod\dist\$ModName.pak."

    $pak = Get-ChildItem -Path $DevKit -Filter "$ModName*.pak" -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($pak) {
        $dist = "D:\MyDev\conan-mod\dist"
        if (-not (Test-Path $dist)) { New-Item -ItemType Directory -Path $dist | Out-Null }
        Copy-Item $pak.FullName "$dist\$ModName.pak" -Force
        Write-Host "[cook] FOUND + copied -> $dist\$ModName.pak  ($($pak.Length) bytes)"
    } else {
        Write-Host "[cook] No $ModName*.pak found yet -- use the GUI steps above, then re-run -Mode cook to copy it into dist\."
    }
    return
}
