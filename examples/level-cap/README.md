# Example: raise the level cap 60 → 120

A complete, working example of a **DataTable-override** mod built fully headless. No GUI,
no `ModController`, no Blueprint. It replaces the three base progression tables with extended
120-level versions.

Replace `ExampleMod` below with your own mod name throughout.

## The one-command way
All five steps below are done for you by the orchestrator:
```powershell
.\tools\exileforge.ps1 -DevKit "C:\ConanDevKit" -Mod "ExampleMod" -Cap 120
```
The rest of this page explains what that command does, in case you want to change the curve or
build a different override.

## 1. Generate the level rows
`tools/ef_levels.py` reads the vanilla CSV dumps and writes the extended `*.ext.csv` rows
(levels 61→N). The XP curve is a smooth continuation of vanilla: it keeps vanilla's near-constant
second difference in the per-level delta, so no value needs hand-calibrating. The dumps come from
`ef_editor.py` mode `dump`, which exports the live vanilla tables first.

The three vanilla tables (UE 5.6 / Enhanced):
| Purpose | Asset | Row struct | Rows (vanilla) |
|---|---|---|---|
| XP thresholds | `/Game/Systems/Progression/DT_ExperienceSystemLevel` | `STR_ExperienceSystemLevel` | 60 (`LevelStart`,`LevelEnd`) |
| Attribute points | `/Game/Systems/Progression/DT_AttributeSystem` | `STR_AttributeSystem` | 60 (0-indexed; `CostPerPoint`,`RewardPerLevel`) |
| Feat points | `/Game/Systems/Progression/DT_FeatsPerLevel` | `STR_FeatsPerLevel` | 60 (`FeatPoints`) |

> XP table is **cumulative** (`LevelStart`/`LevelEnd`). Attribute table is **0-indexed**.

## 2. Create the override tables (headless Unreal Python)
`ef_editor.py` mode `override` duplicates each core table into the mod's `Content`
overlay at the **core relative path** and fills it to 120 rows:
```
/Game/Mods/ExampleMod/Content/Systems/Progression/DT_ExperienceSystemLevel
/Game/Mods/ExampleMod/Content/Systems/Progression/DT_AttributeSystem
/Game/Mods/ExampleMod/Content/Systems/Progression/DT_FeatsPerLevel
```
Because the mod `Content` folder overlays `/Game`, these cook to
`/Game/Systems/Progression/DT_*` and **replace the base tables**.

## 3. Point CookInfo.ini at them
`<DevKit>\UE4\Content\Mods\ExampleMod\Local\CookInfo.ini`:
```ini
[/CookInfo]
FilesToCook=Mods/ExampleMod/Content/Systems/Progression/DT_ExperienceSystemLevel.uasset
FilesToCook=Mods/ExampleMod/Content/Systems/Progression/DT_AttributeSystem.uasset
FilesToCook=Mods/ExampleMod/Content/Systems/Progression/DT_FeatsPerLevel.uasset
```

## 4. Build headless
```bat
"<DevKit>\Engine\Build\BatchFiles\RunUAT.bat" -NoCompile BuildMod ^
    -Mod=ExampleMod -Project="<DevKit>/UE4/ConanSandbox.uproject" ^
    -Cook -Pak -Compress -ScriptDir="<DevKit>/UE4/"
```
Output: `<DevKit>\UE4\Saved\Mods\ExampleMod\Output\ExampleMod.pak`.

## 5. Install
- **Server:** copy the `.pak` to `…/ConanSandbox/Mods/`, add `*ExampleMod.pak` to
  `Mods/modlist.txt`, restart. It mounts as an IoStore container and overrides the tables.
- **Client:** copy the same `.pak` to `…\Conan Exiles\ConanSandbox\Mods\`, enable it in
  Main Menu → Mods (same order as the server).

Now characters can reach level 120. Remove the mod and characters above 60 reset to 60
(standard Conan behaviour).
