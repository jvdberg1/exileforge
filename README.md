# ExileForge

A command-line workflow for building Conan Exiles **Enhanced** (UE 5.6) mods. You cook and
package a `.pak` without opening the editor UI. This repo also documents the setup steps and
failure modes that the official docs skip.

Worked example: raising the player level cap 60 -> 120 by overriding the game's
progression DataTables.

Verified on the Conan Exiles **Enhanced Dev Kit**, UE `5.6.1-366792 (++exiles+release)`, Windows.

> Building Blueprint **logic** mods (custom items, abilities, recall, GUI hooks)? See the sibling
> repo [KismetForge](https://github.com/jvdberg1/kismetforge): same headless cook + deploy, plus
> generating Blueprint graphs as T3D you paste once. ExileForge stays focused on headless
> DataTable-override mods.

---

## What you need (prerequisites)

You need a **Windows PC**. The Dev Kit is Windows-only. For testing, all three roles below can
run on the same machine.

| Thing | Why you need it | Where to get it |
|---|---|---|
| Conan Exiles Dev Kit | Author, cook, and pack the mod. It bundles its own Python and build tool. | Epic Games Store (Section 1) |
| A Conan Exiles dedicated server | Host the mod so you and players can join. | Your host, or run one locally via SteamCMD app `443030` |
| Conan Exiles (the game) | Join the server and see the mod in-game. | Steam |
| Git (optional) | Clone this repo. Or click the green **Code** button on GitHub and **Download ZIP**. | https://git-scm.com |

**You do not need to install Python.** The Dev Kit ships Python here:

```
<DevKit>\Engine\Binaries\ThirdParty\Python3\Win64\python.exe
```

One script runs as plain Python with that interpreter (`ef_levels.py`). The DataTable editor
(`ef_editor.py`) runs **inside** the Dev Kit's editor through `UnrealEditor-Cmd.exe
-run=pythonscript`, so it needs no separate Python at all. The orchestrator `exileforge.ps1`
calls both for you (see Quick start), so you normally run neither by hand.

**You do not need a C++ compiler or Visual Studio** for data-driven mods like the level-cap
example. C++ only matters for code mods, which the installed-build Dev Kit cannot compile anyway.

---

## How the pieces fit together

There are three roles. On one PC for testing, they are the same machine.

1. **Dev Kit (build).** You edit or add assets inside the modkit project, under your mod folder.
   Then `RunUAT BuildMod` cooks and packs them into one `<ModName>.pak`.
2. **Server (host).** You drop that `.pak` into the server's `Mods\` folder and list it in
   `Mods\modlist.txt`. The server loads it on start.
3. **Client (play).** You put the same `.pak` in the game's `Mods\` folder and enable it in the
   in-game mod menu. The client's mods must match the server's to connect.

```
   [Dev Kit]  edit assets  ->  RunUAT BuildMod  ->  <ModName>.pak
                                                       |
                        +------------------------------+------------------------------+
                        v                                                             v
   [Server]  Mods\<ModName>.pak + add to modlist.txt + restart      [Client]  Mods\<ModName>.pak + enable in Main Menu > Mods
                        \                                                             /
                         +-------------------  client joins server  ----------------+
```

Each role's folders:

```
Dev Kit mod source : <DevKit>\UE4\Content\Mods\<ModName>\
Built pak output   : <DevKit>\UE4\Saved\Mods\<ModName>\Output\<ModName>.pak
Server mods        : <ConanServer>\ConanSandbox\Mods\           (+ modlist.txt)
Game client mods   : <Steam>\steamapps\common\Conan Exiles\ConanSandbox\Mods\
```

---

## Quick start (one command)

Once the Dev Kit is installed (Section 1), `exileforge.ps1` builds the whole level-cap mod for
you. Open PowerShell in this repo and run:

```powershell
.\tools\exileforge.ps1 -DevKit "C:\ConanDevKit" -Mod "MyLevelMod" -Cap 120
```

That one command creates the mod if it does not exist, dumps the vanilla progression tables,
generates the extended rows, writes the override tables into the mod, and cooks and packs the
`.pak`. You edit no `.py` files and open no editor window. The result:

```
<DevKit>\UE4\Saved\Mods\MyLevelMod\Output\MyLevelMod.pak
```

Then install it: copy that `.pak` to the server's `Mods\` and add `*MyLevelMod.pak` to
`Mods\modlist.txt`, and copy the same `.pak` to the client's `Mods\` and enable it in
**Main Menu > Mods** (Section 7, step 5).

The sections below explain each piece, in case you want to build something other than a level cap.

---

## 1. Get the Dev Kit (Epic Games Store)

The Dev Kit is free, but it only ships through the Epic Games Store.

1. **Make an Epic Games account** at https://www.epicgames.com if you do not have one.
2. **Install the Epic Games Launcher**: https://store.epicgames.com/en-US/download . Run it and sign in.
3. **Find the Dev Kit.** In the launcher, open **Store** and search `Conan Exiles Dev Kit`
   (it also lists as *Conan Exiles Enhanced Dev Kit*). Confirm the price reads **Free**.
4. **Claim it.** Click **Get**, then complete the free checkout. It now sits in your **Library**.
5. **Install it.** Open **Library** (check a **Modding** tab/filter if it is not in the main grid),
   click **Install**, and set a **short install path** such as `C:\ConanDevKit`. Long paths break
   cooks later. Budget around **160 GB** of disk; the download is large.
6. **First launch.** The first start compiles shaders and can take 30 to 60 minutes. Let it finish.
   Dismiss any "new version" or message-of-the-day popups.

Owning the game on Steam is fine. The Dev Kit is a separate Epic product and needs no Steam link.

After install, your Dev Kit root (referred to below as `<DevKit>`) contains:

```
<DevKit>\RunDevKit.bat                                  launcher (passes -ModDevKit)
<DevKit>\Engine\Binaries\Win64\UnrealEditor.exe        the editor
<DevKit>\Engine\Binaries\Win64\UnrealEditor-Cmd.exe    headless editor / Python host
<DevKit>\Engine\Build\BatchFiles\RunUAT.bat            the build tool
<DevKit>\UE4\ConanSandbox.uproject                     the modkit project
<DevKit>\UE4\Content\Mods\<YourMod>\                   your mod lives here
```

---

## 2. Launch the Dev Kit so the mod tools appear

The modding UI only loads when the editor starts with the **`-ModDevKit`** flag. Launch it one
of two ways:

- Double-click **`<DevKit>\RunDevKit.bat`**, or
- Click **Launch** on the Dev Kit in the Epic Games Launcher.

Both run `UnrealEditor.exe <DevKit>\UE4\ConanSandbox.uproject -ModDevKit`. The mod window then
appears under the editor's **Window** menu as **Conan Exiles DevKit**.

Starting the bare `UnrealEditor.exe` skips the flag, and then no mod menu, toolbar, or window
exists anywhere. If you cannot find the mod tools, this is almost always the cause.

---

## 3. Build a mod headless (one command)

```bat
"<DevKit>\Engine\Build\BatchFiles\RunUAT.bat" -NoCompile BuildMod ^
    -Mod=<ModName> ^
    -Project="<DevKit>/UE4/ConanSandbox.uproject" ^
    -Cook -Pak -Compress ^
    -ScriptDir="<DevKit>/UE4/"
```

`BuildMod` cooks three platforms (Windows, WindowsServer, LinuxServer) and packs the `.pak` in
one run. The cook takes about 8 minutes.

- **Include `-ScriptDir=<DevKit>/UE4/`.** Omit it and UAT reports `Failed to find command BuildMod`.
- `BuildMod` reads the asset list from `<DevKit>\UE4\Content\Mods\<ModName>\Local\CookInfo.ini`
  (the editor writes this from **Choose Assets For Cook**; you can also write it by hand, format below).
- Output: `<DevKit>\UE4\Saved\Mods\<ModName>\Output\<ModName>.pak` (per-platform IoStore
  `.utoc`/`.ucas` plus `modinfo.json`).
- The command's source spec: `<DevKit>\UE4\Build\ModDevKit.Automation\BuildMod.cs`.

To change a mod later, edit its assets, rerun this one command, then redeploy. No editor needed.

---

## 4. CookInfo.ini format

Path: `<DevKit>\UE4\Content\Mods\<ModName>\Local\CookInfo.ini`. Each `FilesToCook` path is
relative to `UE4/Content/`:

```ini
[/CookInfo]
FilesToCook=Mods/<ModName>/Content/Systems/Progression/DT_ExperienceSystemLevel.uasset
FilesToCook=Mods/<ModName>/Content/Systems/Progression/DT_AttributeSystem.uasset
FilesToCook=Mods/<ModName>/Content/Systems/Progression/DT_FeatsPerLevel.uasset
```

---

## 5. Replace a base-game DataTable (the overlay override)

A mod's `Content` folder overlays `/Game`. An asset you author at
`/Game/Mods/<ModName>/Content/Systems/Progression/DT_ExperienceSystemLevel` cooks to
`.../ConanSandbox/Content/Systems/Progression/DT_ExperienceSystemLevel`. The cooker strips the
`Mods/<ModName>/Content/` prefix, so the package becomes `/Game/Systems/Progression/DT_ExperienceSystemLevel`
and replaces the base table when the pak mounts.

A full-table replace needs no `ModController` and no Blueprint. Duplicate the core table into the
mod overlay at the matching path, fill it with new rows, and cook.

---

## 6. Edit DataTables headless (Unreal Python)

Run Python inside the Dev Kit without a window:

```bat
"<DevKit>\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "<DevKit>\UE4\ConanSandbox.uproject" ^
    -run=pythonscript -script="ef_editor.py" -unattended -nopause -nosplash -stdout
```

The functions you need (see `tools/ef_editor.py`):

- `unreal.DataTableFunctionLibrary.export_data_table_to_csv_file(table, path)` dumps a table to CSV.
- `unreal.EditorAssetLibrary.duplicate_asset(core, "/Game/Mods/<Mod>/Content/<core path>")` copies a
  core table into the mod overlay and keeps its row struct.
- `unreal.DataTableFunctionLibrary.fill_data_table_from_csv_string(table, csv)` writes the rows.
- `unreal.EditorAssetLibrary.save_asset(path)` saves.

Stock Unreal Python creates and edits assets and DataTables. It cannot author Blueprint
event-graph node logic. Chat commands, UMG, and similar logic still need the editor GUI, because
the installed-build Dev Kit cannot compile a C++ plugin either. Data-driven mods automate end to
end; logic mods do not.

### The scripts need no editing

Every script takes its settings as arguments or environment variables. Nothing inside them is
hardcoded to one machine, so you never open them in an editor:

- **`tools/exileforge.ps1`** (the orchestrator): pass `-DevKit`, `-Mod`, and `-Cap`.
- **`tools/ef_editor.py`** (runs in the editor): reads `EF_MOD`, `EF_WORKDIR`, `EF_MODE`, which the
  orchestrator sets for you. To run it by hand, set those three variables first.
- **`tools/ef_levels.py`** (plain Python): `python ef_levels.py <workdir> <cap>`. Run it with the
  Dev Kit's bundled interpreter so you install nothing:

```bat
"<DevKit>\Engine\Binaries\ThirdParty\Python3\Win64\python.exe" tools\ef_levels.py C:\conan_work 120
```

---

## 7. Worked example: level cap 60 to 120

See [`examples/level-cap/`](examples/level-cap/). The Quick start runs all of this in one
command. Under the hood `exileforge.ps1` does these steps:

1. Creates the mod scaffold and `modinfo.json` if the mod does not exist yet.
2. `ef_editor.py` (mode `dump`) exports the three vanilla progression tables to a scratch folder.
3. `ef_levels.py` writes the XP, attribute, and feat rows past 60, calibrated to vanilla.
4. `ef_editor.py` (mode `override`) duplicates the three core tables into the mod overlay and fills
   them to your cap.
5. Writes `CookInfo.ini` listing the three tables, then runs the `RunUAT BuildMod` command from
   section 3.

Then install it: copy the `.pak` to the server's `Mods/`, add `*<ModName>.pak` to
`Mods/modlist.txt`, restart. Copy the same `.pak` to the client's
`...\Conan Exiles\ConanSandbox\Mods\` and enable it in **Main Menu > Mods** in the same order as
the server.

Characters can now reach 120. Remove the mod and any character above 60 resets to 60, which is
standard Conan behaviour for level mods.

---

## 8. Failure modes and fixes

| Symptom | Cause and fix |
|---|---|
| No mod menu, toolbar, or window | Launched without `-ModDevKit`. Use `RunDevKit.bat`. |
| `Failed to find command BuildMod` | Add `-ScriptDir=<DevKit>/UE4/`. |
| `Unable to find package for cooking` / `ExitCode 28` | Asset is outside the mod's `Content` folder, or `CookInfo.ini` points at the wrong path. Keep assets under `Mods/<ModName>/Content/`. |
| Mod mounts, `LogModController: Invalid class`, nothing changes | A `ModController` was rejected. For a table replace, drop the controller and use the overlay override (section 5). |
| A mod folder shows empty after you edit assets headless | Asset-registry desync. Verify with a fresh headless load, then relaunch the editor. |
| `.uasset` will not import via drag-and-drop in Explorer | That is not the workflow. Assets sit under the project's `Content/` and the registry scans them. |

---

## 9. What automates and what does not

| Task | Headless? |
|---|---|
| Edit or replace DataTables | Yes, via Unreal Python and the overlay override |
| Cook and package the `.pak` | Yes, via `RunUAT BuildMod` |
| Deploy to a server (`scp`, `modlist.txt`, restart) | Yes |
| Build Blueprint node graphs (chat commands, UMG) | No. Editor GUI or C++ |

---

## License

MIT. See [LICENSE](LICENSE). Contributions welcome.

Not affiliated with Funcom or Inflexion Games. "Conan Exiles" is their trademark.
