# ExileForge -- one-command headless mod build for Conan Exiles Enhanced (UE5).
#
#   .\exileforge.ps1 -DevKit "C:\ConanDevKit" -Mod "MyLevelMod" [-Cap 120] [-WorkDir <dir>]
#
# Does everything: creates the mod if needed, dumps the vanilla progression
# tables, generates extended rows to <Cap>, writes the override tables into the
# mod, writes CookInfo.ini, then cooks + packs the .pak. No editor, no .py edits.
# Output: <DevKit>\UE4\Saved\Mods\<Mod>\Output\<Mod>.pak

param(
    [Parameter(Mandatory = $true)][string] $DevKit,
    [Parameter(Mandatory = $true)][string] $Mod,
    [int] $Cap = 120,
    [string] $WorkDir = ""
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $WorkDir) { $WorkDir = Join-Path $env:TEMP "exileforge\$Mod" }

$editor   = Join-Path $DevKit "Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
$uproject = Join-Path $DevKit "UE4\ConanSandbox.uproject"
$runuat   = Join-Path $DevKit "Engine\Build\BatchFiles\RunUAT.bat"
$python   = Join-Path $DevKit "Engine\Binaries\ThirdParty\Python3\Win64\python.exe"
$modroot  = Join-Path $DevKit "UE4\Content\Mods\$Mod"
$efpy     = Join-Path $here "ef_editor.py"
$lvpy     = Join-Path $here "ef_levels.py"

foreach ($p in @($editor, $uproject, $runuat)) {
    if (-not (Test-Path $p)) { throw "Not found: $p  (is -DevKit correct?)" }
}
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

# 1. create the mod scaffold if it does not exist yet
if (-not (Test-Path (Join-Path $modroot "modinfo.json"))) {
    Write-Host "[exileforge] creating mod scaffold: $Mod"
    New-Item -ItemType Directory -Force -Path $modroot | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $modroot "Local") | Out-Null
    $modinfo = [ordered]@{
        name = $Mod; description = ""; changeNote = ""; author = ""; authorUrl = ""
        versionMajor = 1; versionMinor = 0; versionBuild = 0; bRequiresLoadOnStartup = $false
        steamPublishedFileId = ""; steamTestLivePublishedFileId = ""; steamWorkshopFileIds = @{}
        steamVisibility = 2; folderName = $Mod; devkitRevisionNumber = 0; devkitSnapshotId = 0
        fileSize = 0; minimumVersion = "Enhanced"
    } | ConvertTo-Json
    Set-Content -Path (Join-Path $modroot "modinfo.json") -Value $modinfo -Encoding UTF8
}

function Invoke-Editor([string] $mode) {
    $env:EF_MOD = $Mod; $env:EF_WORKDIR = $WorkDir; $env:EF_MODE = $mode
    & $editor "$uproject" -run=pythonscript -script="$efpy" -unattended -nopause -nosplash -stdout
    if ($LASTEXITCODE -ne 0) { throw "editor ($mode) failed: exit $LASTEXITCODE" }
}

Write-Host "[exileforge] 1/4 dumping vanilla progression tables -> $WorkDir"
Invoke-Editor "dump"

Write-Host "[exileforge] 2/4 generating level rows to cap $Cap"
& $python "$lvpy" "$WorkDir" $Cap
if ($LASTEXITCODE -ne 0) { throw "ef_levels failed: exit $LASTEXITCODE" }

Write-Host "[exileforge] 3/4 writing override tables into the mod"
Invoke-Editor "override"

# CookInfo.ini -- the asset list BuildMod cooks
$cookInfo = Join-Path $modroot "Local\CookInfo.ini"
$lines = @("[/CookInfo]")
foreach ($n in @("DT_ExperienceSystemLevel", "DT_AttributeSystem", "DT_FeatsPerLevel")) {
    $lines += "FilesToCook=Mods/$Mod/Content/Systems/Progression/$n.uasset"
}
Set-Content -Path $cookInfo -Value $lines -Encoding ASCII

Write-Host "[exileforge] 4/4 cooking + packing (RunUAT BuildMod, ~8 min)"
& $runuat -NoCompile BuildMod "-Mod=$Mod" "-Project=$uproject" -Cook -Pak -Compress "-ScriptDir=$DevKit/UE4/"
if ($LASTEXITCODE -ne 0) { throw "BuildMod failed: exit $LASTEXITCODE" }

$pak = Join-Path $DevKit "UE4\Saved\Mods\$Mod\Output\$Mod.pak"
if (Test-Path $pak) {
    Write-Host ("[exileforge] DONE -> {0} ({1} bytes)" -f $pak, (Get-Item $pak).Length)
    Write-Host "[exileforge] copy it to your server Mods\ + modlist.txt, and your client Mods\."
} else {
    Write-Host "[exileforge] build finished but pak not found; check the log above."
}
