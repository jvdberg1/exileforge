# ExileForge — Headless Mod Kit for Conan Exiles Enhanced (UE5)

Build Conan Exiles **Enhanced** (UE 5.6) mods **entirely from the command line** — cook
and package a `.pak` with **no GUI clicking** — plus the hard‑won gotchas that the official
docs don't make clear. This came out of a full day of dead‑ends; the goal here is that nobody
else loses that day.

Worked example included: raising the **player level cap 60 → 120** by overriding the game's
progression DataTables.

> Verified on: Conan Exiles **Enhanced Dev Kit**, UE `5.6.1-366792 (++exiles+release)`, Windows.

---

## TL;DR — the three things that actually matter

1. **The Dev Kit modding UI only appears if you launch with `-ModDevKit`.**
   Launch via `<DevKit>\RunDevKit.bat` (which is just
   `UnrealEditor.exe <DevKit>\UE4\ConanSandbox.uproject -ModDevKit`) or from the Epic launcher.
   If you start the bare `UnrealEditor.exe`, **there is no mod menu/toolbar at all** — the
   "Conan Exiles DevKit" window (under the **Window** menu) is simply absent. Hours vanish here.

2. **You can build the whole mod headless with one command** (no editor window):
   ```bat
   "<DevKit>\Engine\Build\BatchFiles\RunUAT.bat" -NoCompile BuildMod ^
       -Mod=<ModName> ^
       -Project="<DevKit>/UE4/ConanSandbox.uproject" ^
       -Cook -Pak -Compress ^
       -ScriptDir="<DevKit>/UE4/"
   ```
   `BuildMod` cooks (Windows + WindowsServer + LinuxServer) **and** packs in one call (~8 min).
   - **`-ScriptDir=<DevKit>/UE4/` is mandatory.** Without it: `Failed to find command BuildMod`.
   - It reads the asset list from `<DevKit>\UE4\Content\Mods\<ModName>\Local\CookInfo.ini`
     (the GUI's *"Choose Assets For Cook"*). You can write that file yourself (format below).
   - Output: `<DevKit>\UE4\Saved\Mods\<ModName>\Output\<ModName>.pak`
     (per‑platform IoStore `.utoc/.ucas` + `modinfo.json`).
   - Source of truth for the command: `<DevKit>\UE4\Build\ModDevKit.Automation\BuildMod.cs`.

3. **To replace a base‑game asset (e.g. a DataTable), use the mod's `Content` overlay.**
   A mod's `Content` folder is an overlay of `/Game`. An asset authored at
   `/Game/Mods/<ModName>/Content/Systems/Progression/DT_ExperienceSystemLevel`
   **cooks to** `…/ConanSandbox/Content/Systems/Progression/DT_ExperienceSystemLevel`
   (the `Mods/<ModName>/Content/` prefix is stripped) — i.e. package
   `/Game/Systems/Progression/DT_ExperienceSystemLevel`, which **overrides the base table**
   when the mod pak mounts. **No `ModController` / `MergeDataTables` Blueprint needed** for a
   full‑table replace.

---

## `CookInfo.ini` format

`<DevKit>\UE4\Content\Mods\<ModName>\Local\CookInfo.ini` — paths are **relative to `UE4/Content/`**:

```ini
[/CookInfo]
FilesToCook=Mods/<ModName>/Content/Systems/Progression/DT_ExperienceSystemLevel.uasset
FilesToCook=Mods/<ModName>/Content/Systems/Progression/DT_AttributeSystem.uasset
FilesToCook=Mods/<ModName>/Content/Systems/Progression/DT_FeatsPerLevel.uasset
```

---

## Editing DataTables headlessly (Unreal Python)

Run Python inside the Dev Kit headlessly:
```bat
"<DevKit>\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "<DevKit>\UE4\ConanSandbox.uproject" ^
    -run=pythonscript -script="edit_datatables.py" -unattended -nopause -nosplash -stdout
```
Key API (see `tools/edit_datatables.py`):
- `unreal.DataTableFunctionLibrary.export_data_table_to_csv_file(table, path)` — dump a table.
- `unreal.EditorAssetLibrary.duplicate_asset(core, "/Game/Mods/<Mod>/Content/<core path>")` —
  copy a core table into the mod overlay (keeps the right row struct).
- `unreal.DataTableFunctionLibrary.fill_data_table_from_csv_string(table, csv)` — write rows.
- `unreal.EditorAssetLibrary.save_asset(path)`.

> Note: stock Unreal Python can create/edit **assets and DataTables**, but it **cannot author
> Blueprint event‑graph node logic** — that still needs the editor GUI (or a C++ plugin, which
> the installed‑build Dev Kit can't compile). So data‑driven mods automate cleanly; logic mods
> (chat commands, etc.) do not.

---

## Worked example: level cap 60 → 120

See [`examples/level-cap/`](examples/level-cap/). In short:
1. `tools/generate_levels.py` builds the XP/attribute/feat rows past 60 (calibrated to vanilla).
2. `tools/edit_datatables.py` (mode `override`) duplicates the 3 core progression tables into
   `/Game/Mods/<Mod>/Content/Systems/Progression/` and fills them to 120 rows.
3. Write `CookInfo.ini` listing those 3 assets.
4. Run the `RunUAT BuildMod` command above.
5. Drop the `.pak` in the server's `Mods/` + add `*<ModName>.pak` to `modlist.txt`, restart.
   Put the same pak in the client's `…\Conan Exiles\ConanSandbox\Mods\` and enable it.

Cap is now 120 (the 120‑row table overrides the base 60‑row one). Removing the mod resets
characters above 60 back to 60 (normal Conan behaviour for level mods).

---

## Gotchas that cost the day (so they don't cost yours)

- **No mod UI?** You launched without `-ModDevKit`. Use `RunDevKit.bat`.
- **`Failed to find command BuildMod`** → add `-ScriptDir=<DevKit>/UE4/`.
- **`Unable to find package for cooking` / `ExitCode 28`** → the asset isn't inside the mod's
  `Content` folder, or `CookInfo.ini` points at the wrong path. Assets **must** live under
  `Mods/<ModName>/Content/…`.
- **Mod loads but `LogModController: Invalid class` and nothing changes** → you tried a
  `ModController` that wasn't accepted. For a straight table replace, skip the controller and
  use the **overlay override** instead (above).
- **Editor shows a mod folder as empty after editing assets headlessly** → asset‑registry
  desync; verify with a fresh **headless** load, don't trust the running GUI. Re‑launch.
- **`.uasset` can't be dragged/imported via File Explorer** — that's not how it works; assets
  belong on disk under the project's `Content/` and the registry scans them.

---

## What automates and what doesn't

| Task | Headless / CLI? |
|---|---|
| Edit/replace DataTables | ✅ Unreal Python + overlay override |
| Cook + package the `.pak` | ✅ `RunUAT BuildMod` |
| Deploy to a server (`scp` + `modlist.txt` + restart) | ✅ |
| Build Blueprint **node graphs** (chat commands, UMG) | ❌ editor GUI (or C++) |

---

## License

MIT — see [LICENSE](LICENSE). Community contributions welcome.

*Not affiliated with Funcom / Inflexion Games. "Conan Exiles" is their trademark.*
