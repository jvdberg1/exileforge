#!/usr/bin/env python3
# edit_datatables.py
# -----------------------------------------------------------------------------
# Runs INSIDE the Conan Exiles Enhanced Dev Kit, driven by cook.ps1 via:
#   UnrealEditor-Cmd.exe <ConanSandbox.uproject> -run=pythonscript \
#       -script="D:\MyDev\conan-mod\tools\edit_datatables.py"
# Uses the Unreal Editor Python API (the 'unreal' module, editor-only).
#
# Modes (env CONAN_MOD_MODE, set by cook.ps1):
#   "discover" -> enumerate DataTable / CurveTable assets matching leveling +
#                 follower keywords; print object paths, row counts, row names,
#                 and row-struct names so we learn the REAL asset names + schema.
#   "inspect"  -> export the 3 real progression tables to D:\tmp\conan_export so
#                 we get exact columns + L60 values for calibration; hunt the
#                 active-follower-limit across Blueprints.
#   "apply"    -> duplicate ONLY the leveling + follower tables into the mod
#                 content folder, write values from data\levels.csv (rows up to
#                 SERVER_CAP) and the follower limit = ACTIVE_FOLLOWERS, save.
#
# HONEST STATUS: ASSET_* + COLUMN_MAP are PLACEHOLDERS until discover is run.
# Real install:
#   DevKit  C:\Program Files\Epic Games\CEUE5Devkit
#   mod dir <DevKit>\UE4\Content\Mods\ExampleMod  (already created)
# -----------------------------------------------------------------------------

import os
import csv
import traceback

try:
    import unreal
except ImportError:
    raise SystemExit("Run via UnrealEditor-Cmd.exe inside the Dev Kit (cook.ps1).")

# ---- config -----------------------------------------------------------------
MODE             = os.environ.get("CONAN_MOD_MODE", "discover")
MOD_NAME         = "ExampleMod"
SERVER_CAP       = 120
ACTIVE_FOLLOWERS = 5
LEVELS_CSV       = r"D:\MyDev\conan-mod\data\levels.csv"

# PLACEHOLDERS -- fill from discover output before running apply:
ASSET_LEVEL_TABLE    = "/Game/TODO_FILL_FROM_DISCOVER/DT_PlayerLevels"
ASSET_FOLLOWER_ASSET = "/Game/TODO_FILL_FROM_DISCOVER/FollowerLimit"
MOD_CONTENT_ROOT     = "/Game/Mods/%s" % MOD_NAME

COLUMN_MAP = {
    "XP_To_Next":       "TODO_xp_field",
    "Attribute_Points": "TODO_attr_field",
    "Feat_Points":      "TODO_feat_field",
}

LEVEL_HINTS    = ["level", "xp", "experience", "attribute", "feat",
                  "knowledge", "progression", "rank"]
FOLLOWER_HINTS = ["follower", "thrall", "minion", "pet", "companion",
                  "population", "activefollower"]


def _log(msg):
    unreal.log("[ExampleMod] " + str(msg))


def _err(msg):
    unreal.log_error("[ExampleMod] " + str(msg))


def _engine_info():
    try:
        v = unreal.SystemLibrary.get_engine_version()
        _log("engine version: %s" % v)
    except Exception as e:
        _log("engine version unavailable: %s" % e)


def _all_assets_by_class(cls):
    """Return assets of a class, tolerating UE API differences across versions."""
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    # UE5 path-based API
    try:
        tap = unreal.TopLevelAssetPath("/Script/Engine", cls)
        return list(ar.get_assets_by_class(tap, True))
    except Exception:
        pass
    # older string-based API
    try:
        return list(ar.get_assets_by_class(cls, True))
    except Exception as e:
        _err("get_assets_by_class failed for %s: %s" % (cls, e))
        return []


def discover():
    _engine_info()
    for cls in ("DataTable", "CurveTable"):
        assets = _all_assets_by_class(cls)
        _log("class %s: %d total assets" % (cls, len(assets)))
        hits = []
        for a in assets:
            try:
                path = str(a.package_name)
            except Exception:
                continue
            low = path.lower()
            if any(h in low for h in LEVEL_HINTS):
                hits.append(("LEVEL?", path))
            elif any(h in low for h in FOLLOWER_HINTS):
                hits.append(("FOLLOWER?", path))
        _log("  %d candidate %s assets matching hints" % (len(hits), cls))
        for tag, path in sorted(hits):
            _log("%-10s %-11s %s" % (tag, cls, path))
            try:
                obj = unreal.load_asset(path)
                if obj is None:
                    _log("    (load returned None)")
                    continue
                rows = unreal.DataTableFunctionLibrary.get_data_table_row_names(obj)
                if rows:
                    _log("    rows: %d (first 8: %s)" %
                         (len(rows), [str(r) for r in rows[:8]]))
                try:
                    rs = obj.get_editor_property("row_struct")
                    if rs:
                        _log("    row_struct: %s" % rs.get_name())
                except Exception:
                    pass
            except Exception as e:
                _log("    (could not inspect: %s)" % e)
    _log("---- discover done. Paste LEVEL table + FOLLOWER asset paths + the "
         "row_struct field names into ASSET_* and COLUMN_MAP, then run apply. ----")


INSPECT_TABLES = [
    "/Game/Systems/Progression/DT_ExperienceSystemLevel",
    "/Game/Systems/Progression/DT_AttributeSystem",
    "/Game/Systems/Progression/DT_FeatsPerLevel",
]
EXPORT_DIR = r"D:\tmp\conan_export"


def inspect():
    _engine_info()
    funcs = [f for f in dir(unreal.DataTableFunctionLibrary) if not f.startswith("_")]
    _log("DataTableFunctionLibrary methods: " + ", ".join(funcs))

    # export the 3 progression tables to disk (CSV/JSON) for offline reading
    try:
        at = unreal.AssetToolsHelpers.get_asset_tools()
    except Exception as e:
        _err("asset tools unavailable: %s" % e)
        at = None
    if at:
        for p in INSPECT_TABLES:
            try:
                at.export_assets([p], EXPORT_DIR)
                _log("exported %s -> %s" % (p, EXPORT_DIR))
            except Exception as e:
                _err("export failed %s: %s" % (p, e))
        # also try a JSON string dump via whatever method exists
        for p in INSPECT_TABLES:
            try:
                t = unreal.load_asset(p)
                if hasattr(unreal.DataTableFunctionLibrary, "get_data_table_as_json"):
                    js = unreal.DataTableFunctionLibrary.get_data_table_as_json(t)
                    _log("JSON %s (first 400): %s" % (p.split("/")[-1], str(js)[:400]))
            except Exception as e:
                _log("json dump skipped %s: %s" % (p, e))

    # hunt the active-follower-limit across Blueprints
    blu = _all_assets_by_class("Blueprint")
    _log("Blueprint assets: %d" % len(blu))
    want = ["follower", "thrall", "minion", "companion", "pet"]
    lim = ["max", "limit", "active", "cap", "population", "count", "number", "amount"]
    n = 0
    for a in blu:
        try:
            path = str(a.package_name)
        except Exception:
            continue
        low = path.lower()
        if any(w in low for w in want) and any(l in low for l in lim):
            _log("FOLLOWER-BP? " + path)
            n += 1
    _log("follower-limit BP candidates: %d (if 0, the limit is likely a pawn/"
         "component default or C++ value -> inspect player/thrall BP defaults next)" % n)
    _log("---- inspect done. Read CSVs under %s offline. ----" % EXPORT_DIR)


def probe():
    """Introspect the Python API for any headless mod build/cook entrypoint."""
    _engine_info()
    names = sorted(dir(unreal))
    def show(label, keys):
        hits = [n for n in names if any(k in n.lower() for k in keys)]
        _log("%s (%d): %s" % (label, len(hits), ", ".join(hits)))
        return hits
    fun = show("Funcom/Dreamworld/Devkit/Conan classes",
               ["dreamworld", "funcom", "devkit", "exiles", "conan", "modkit"])
    show("classes named *mod*", ["mod"])
    for cn in set(fun + [n for n in names if "mod" in n.lower()]):
        try:
            cls = getattr(unreal, cn)
            ms = [m for m in dir(cls) if not m.startswith("_") and
                  any(k in m.lower() for k in ["build", "cook", "pak", "publish", "package"])]
            if ms:
                _log("  %s -> %s" % (cn, ", ".join(ms)))
        except Exception:
            pass
    # global functions too
    gfn = [n for n in names if any(k in n.lower() for k in
           ["buildmod", "cookmod", "modbuild", "packagemod", "publishmod"])]
    _log("global build/cook funcs: " + (", ".join(gfn) if gfn else "NONE"))
    _log("---- probe done. ----")


def dump():
    """Export the 3 progression tables to REAL CSV (rows+values) for offline read."""
    _engine_info()
    if not os.path.isdir(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)
    for p in INSPECT_TABLES:
        name = p.split("/")[-1]
        try:
            t = unreal.load_asset(p)
            cols = unreal.DataTableFunctionLibrary.get_data_table_column_names(t)
            _log("%s columns: %s" % (name, [str(c) for c in cols]))
            csvf = os.path.join(EXPORT_DIR, name + ".csv")
            ok = unreal.DataTableFunctionLibrary.export_data_table_to_csv_file(t, csvf)
            _log("CSV %s -> %s (ok=%s)" % (name, csvf, ok))
        except Exception as e:
            _err("dump failed %s: %s" % (name, e))
            try:
                s = unreal.DataTableFunctionLibrary.export_data_table_to_csv_string(t)
                with open(os.path.join(EXPORT_DIR, name + ".csv"), "w", encoding="utf-8") as f:
                    f.write(s)
                _log("wrote CSV via string for %s" % name)
            except Exception as e2:
                _err("csv string fallback failed %s: %s" % (name, e2))
    _log("---- dump done. Read %s\\*.csv offline. ----" % EXPORT_DIR)


def _read_levels():
    with open(LEVELS_CSV, newline="") as f:
        return list(csv.DictReader(f))


# mod content root (matches the modkit's empty Content folder for this mod)
MOD_ROOT = "/Game/Mods/ExampleMod/Content"
# (core_path, vanilla_60row_csv, extended_120row_csv)
TABLES = [
    ("/Game/Systems/Progression/DT_ExperienceSystemLevel",
     r"D:\tmp\conan_export\DT_ExperienceSystemLevel.csv",
     r"D:\tmp\conan_export\DT_ExperienceSystemLevel.120.csv"),
    ("/Game/Systems/Progression/DT_AttributeSystem",
     r"D:\tmp\conan_export\DT_AttributeSystem.csv",
     r"D:\tmp\conan_export\DT_AttributeSystem.120.csv"),
    ("/Game/Systems/Progression/DT_FeatsPerLevel",
     r"D:\tmp\conan_export\DT_FeatsPerLevel.csv",
     r"D:\tmp\conan_export\DT_FeatsPerLevel.120.csv"),
]


def _find_modcontroller_parent():
    """Derive the ModController base class from an existing DLC ModController's
    parent (those ship in the DevKit)."""
    samples = [
        "/Game/DLC/DLC_Turan/DLC_Turan_Modcontroller",
        "/Game/DLC/DLC_Siptah/DLC_Siptah_Modcontroller",
        "/Game/DLC/Special/BP_Special_ModController",
        "/Game/DLC/DLC_Pict/DLC_Pict_Modcontroller",
    ]
    for sp in samples:
        try:
            bp = unreal.load_asset(sp)
            if not bp:
                continue
            pc = bp.get_editor_property("parent_class")
            if pc:
                _log("derived ModController base %s from %s" % (pc.get_name(), sp))
                return pc, sp
        except Exception as e:
            _log("sample %s failed: %s" % (sp, e))
    return None, None


def exinspect():
    """Introspect /Game/Items/Example_modcontroller: parent, variables (are the
    DataTables variables we could repoint via Python?), and graph pages/nodes."""
    _engine_info()
    EX = "/Game/Items/Example_modcontroller"
    bp = unreal.load_asset(EX)
    _log("loaded %s -> %s" % (EX, type(bp).__name__ if bp else "None"))
    if not bp:
        _err("could not load Example_modcontroller")
        return
    try:
        pc = bp.get_editor_property("parent_class")
        _log("parent_class: %s" % (pc.get_path_name() if pc else None))
    except Exception as e:
        _log("parent_class err: %s" % e)
    # Blueprint variables (repointable via Python if DataTables are vars)
    for prop in ("new_variables",):
        try:
            nv = bp.get_editor_property(prop)
            _log("%s count: %s" % (prop, len(nv) if nv is not None else None))
            for v in (nv or []):
                try:
                    nm = v.get_editor_property("var_name")
                    pt = v.get_editor_property("var_type")
                    cat = pt.get_editor_property("pin_category") if pt else "?"
                    sub = pt.get_editor_property("pin_sub_category_object") if pt else None
                    _log("   var %s : %s / %s" % (nm, cat, sub.get_name() if sub else ""))
                except Exception as e:
                    _log("   var read err: %s" % e)
        except Exception as e:
            _log("%s err: %s" % (prop, e))
    # graph pages + node classes
    for gp in ("ubergraph_pages", "function_graphs", "macro_graphs"):
        try:
            graphs = bp.get_editor_property(gp)
            _log("%s: %s graph(s)" % (gp, len(graphs) if graphs is not None else None))
            for g in (graphs or []):
                try:
                    nodes = g.get_editor_property("nodes")
                    classes = {}
                    for n in (nodes or []):
                        cn = type(n).__name__
                        classes[cn] = classes.get(cn, 0) + 1
                    _log("   graph %s nodes: %s" % (g.get_name(), classes))
                except Exception as e:
                    _log("   nodes err: %s" % e)
        except Exception as e:
            _log("%s err: %s" % (gp, e))
    _log("---- exinspect done. ----")


def mcprobe():
    """Deep introspect ModController: method signatures (docstrings), all editor
    properties (CDO), and the MergeTestRow struct -- to find a DATA-DRIVEN merge
    that needs NO Blueprint graph."""
    _engine_info()
    mc = unreal.ModController
    for m in ("merge_data_tables", "merge_data_tables_with_control_table",
              "remove_data_table_rows", "clear_data_table"):
        try:
            _log("SIG %s :: %s" % (m, (getattr(mc, m).__doc__ or "").strip()))
        except Exception as e:
            _log("sig %s err: %s" % (m, e))
    # CDO + property discovery
    try:
        cdo = unreal.get_default_object(mc)
        cand = ["additional_class_components", "additional_gameplay_tag_tables",
                "additional_sublevels", "data_tables", "data_table_merges",
                "merge_data_table", "control_table", "data_table_control",
                "merge_control_table", "data_table_operations", "tables_to_merge",
                "additional_data_tables", "data_table_merge_control"]
        for n in cand:
            try:
                v = cdo.get_editor_property(n)
                _log("PROP %s = %s" % (n, v))
            except Exception:
                pass
        # brute: any attr name hinting datatable/merge/control on the instance
        hints = [a for a in dir(cdo) if not a.startswith("_") and
                 any(k in a.lower() for k in ("table", "merge", "control", "operation"))]
        _log("CDO attrs ~table/merge/control: %s" % hints)
    except Exception as e:
        _log("cdo err: %s" % e)
    try:
        inst = unreal.ModControllerMergeTestRow()
        fields = [a for a in dir(inst) if not a.startswith("_") and
                  a not in ("cast", "get_editor_property", "set_editor_property",
                            "set_editor_properties", "to_tuple", "static_struct",
                            "is_editable", "reset_editor_property",
                            "is_editor_property_overridden", "export_text",
                            "import_text")]
        _log("ModControllerMergeTestRow fields: %s" % fields)
    except Exception as e:
        _log("merge test row err: %s" % e)
    _log("---- mcprobe done. ----")


def findmc():
    """Diagnostic: locate the ModController base class every possible way."""
    _engine_info()
    # 1. C++ classes exposed to Python
    names = [n for n in dir(unreal) if "modcontroller" in n.lower()
             or "moddatatable" in n.lower() or n.lower() == "modcontroller"]
    _log("unreal attrs ~ModController/ModDataTable: %s" % names)
    if hasattr(unreal, "ModController"):
        ms = [m for m in dir(unreal.ModController) if not m.startswith("_") and
              any(k in m.lower() for k in ["merge", "datatable", "data_table",
              "operation", "row", "overwrite", "add", "table"])]
        _log("ModController methods ~merge/datatable: %s" % ms)
    # 2. inspect DLC sample blueprints multiple ways
    samples = [
        "/Game/DLC/DLC_Turan/DLC_Turan_Modcontroller",
        "/Game/DLC/Special/BP_Special_ModController",
        "/Game/DLC/DLC_Siptah/DLC_Siptah_Modcontroller",
    ]
    for sp in samples:
        try:
            obj = unreal.load_asset(sp)
            _log("sample %s -> %s" % (sp, type(obj).__name__ if obj else "None"))
            if not obj:
                continue
            try:
                pc = obj.get_editor_property("parent_class")
                _log("   parent_class prop: %s" % (pc.get_path_name() if pc else None))
            except Exception as e:
                _log("   parent_class prop err: %s" % e)
            try:
                gc = obj.generated_class()
                _log("   generated_class: %s" % (gc.get_path_name() if gc else None))
                if gc:
                    sup = gc.get_super_class()
                    _log("   super of generated: %s" % (sup.get_path_name() if sup else None))
            except Exception as e:
                _log("   generated_class err: %s" % e)
        except Exception as e:
            _log("sample %s load err: %s" % (sp, e))
    # 3. asset registry: any Blueprint whose name has ModController
    try:
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        bps = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Blueprint"), True)
        hits = [str(a.package_name) for a in bps
                if "modcontroller" in str(a.package_name).lower()]
        _log("BP assets ~ModController (%d): %s" % (len(hits), hits[:15]))
    except Exception as e:
        _err("AR search failed: %s" % e)
    _log("---- findmc done. ----")


def makemc():
    """Create BP_ExampleController (parent = ModController) in the mod so it
    can merge our tables into the core tables. Node graph wired by hand in GUI."""
    _engine_info()
    parent, src = None, None
    # ModController is exposed directly as a C++ class (confirmed via findmc)
    if hasattr(unreal, "ModController"):
        parent, src = unreal.ModController, "unreal.ModController"
    if parent is None:
        parent, src = _find_modcontroller_parent()
    if parent is None:
        _err("ModController base class not found -- cannot create BP")
        return
    bp_path = "%s/BP_ExampleController" % MOD_ROOT
    eal = unreal.EditorAssetLibrary
    if eal.does_asset_exist(bp_path):
        _log("BP already exists: %s" % bp_path)
        return
    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", parent)
    at = unreal.AssetToolsHelpers.get_asset_tools()
    bp = at.create_asset("BP_ExampleController", MOD_ROOT, unreal.Blueprint, factory)
    if bp is None:
        _err("create_asset returned None for %s" % bp_path)
        return
    eal.save_asset(bp_path)
    _log("CREATED %s (parent=%s)" % (bp_path, src))
    listing = eal.list_assets(MOD_ROOT, True, False)
    _log("mod content now (%d): %s" % (len(listing), [str(a) for a in listing]))
    _log("---- makemc done. Now wire ModDataTableOperations in the GUI. ----")


def verify():
    _engine_info()
    eal = unreal.EditorAssetLibrary
    root = "/Game/Mods/ExampleMod"
    try:
        listing = eal.list_assets(root, True, True)
        _log("registry under %s (%d): %s" % (root, len(listing), [str(x) for x in listing]))
    except Exception as e:
        _err("list_assets err: %s" % e)
    for a in ("BP_ExampleController", "DT_ModXP", "DT_ModAttr", "DT_ModFeats"):
        p = "%s/%s" % (root, a)
        ex = eal.does_asset_exist(p)
        _log("exists %s = %s" % (p, ex))
        if not ex:
            continue
        obj = unreal.load_asset(p)
        _log("  loaded: %s" % (type(obj).__name__ if obj else "None"))
        if obj is None:
            continue
        if a.startswith("DT_"):
            try:
                _log("  rows=%d" % len(unreal.DataTableFunctionLibrary.get_data_table_row_names(obj)))
            except Exception as e:
                _log("  rows err: %s" % e)
        else:
            try:
                gc = obj.generated_class()
                sup = gc.get_super_class() if gc else None
                _log("  gen_class=%s parent=%s" % (gc.get_name() if gc else None, sup.get_name() if sup else None))
            except Exception as e:
                _log("  bp class err: %s" % e)
    _log("---- verify done ----")


def override():
    """Correct approach: put 120-row tables in the mod's Content overlay at the
    CORE paths so they cook to /Game/Systems/Progression/* and directly replace
    the base tables (no ModController). Also restore core to vanilla + delete the
    broken ModController/root copies."""
    _engine_info()
    eal = unreal.EditorAssetLibrary
    modroot = "/Game/Mods/ExampleMod"
    for old in ("BP_ExampleController", "DT_ModXP", "DT_ModAttr", "DT_ModFeats"):
        p = "%s/%s" % (modroot, old)
        if eal.does_asset_exist(p):
            eal.delete_asset(p)
            _log("deleted old %s" % p)
    OVR = [
        ("/Game/Systems/Progression/DT_ExperienceSystemLevel",
         r"D:\tmp\conan_export\DT_ExperienceSystemLevel.csv",
         r"D:\tmp\conan_export\DT_ExperienceSystemLevel.120.csv"),
        ("/Game/Systems/Progression/DT_AttributeSystem",
         r"D:\tmp\conan_export\DT_AttributeSystem.csv",
         r"D:\tmp\conan_export\DT_AttributeSystem.120.csv"),
        ("/Game/Systems/Progression/DT_FeatsPerLevel",
         r"D:\tmp\conan_export\DT_FeatsPerLevel.csv",
         r"D:\tmp\conan_export\DT_FeatsPerLevel.120.csv"),
    ]
    for core, vanilla_csv, ext_csv in OVR:
        name = core.split("/")[-1]
        try:
            _log("restored core %s -> %d rows" % (name, _fill(core, vanilla_csv)))
        except Exception as e:
            _err("core restore failed %s: %s" % (name, e))
        dst = "%s/Content/Systems/Progression/%s" % (modroot, name)
        if eal.does_asset_exist(dst):
            eal.delete_asset(dst)
        if not eal.duplicate_asset(core, dst):
            _err("duplicate failed -> %s" % dst)
            continue
        _log("OVERRIDE %s -> %d rows at %s" % (name, _fill(dst, ext_csv), dst))
    try:
        listing = eal.list_assets("%s/Content" % modroot, True, False)
        _log("mod Content overlay now (%d): %s" % (len(listing), [str(x) for x in listing]))
    except Exception as e:
        _err("list err: %s" % e)
    _log("---- override done ----")


def relocate():
    """Move the mod's assets out of the wrong .../Content/ subfolder UP into the
    mod root /Game/Mods/ExampleMod/ (matching Pippi), so the cooked
    ModController is at /Game/Mods/ExampleMod/... and is accepted."""
    _engine_info()
    eal = unreal.EditorAssetLibrary
    src_root = "/Game/Mods/ExampleMod/Content"
    dst_root = "/Game/Mods/ExampleMod"
    # tables first, then the BP (rename_asset updates references either way)
    order = ["DT_ModXP", "DT_ModAttr", "DT_ModFeats", "BP_ExampleController"]
    for a in order:
        s = "%s/%s" % (src_root, a)
        d = "%s/%s" % (dst_root, a)
        if not eal.does_asset_exist(s):
            _log("source missing (already moved?): %s" % s)
            continue
        if eal.does_asset_exist(d):
            eal.delete_asset(d)
        ok = eal.rename_asset(s, d)
        eal.save_asset(d)
        _log("moved %s -> %s (ok=%s)" % (a, d, ok))
    try:
        if eal.does_directory_exist(src_root):
            eal.delete_directory(src_root)
            _log("deleted empty %s" % src_root)
    except Exception as e:
        _log("delete dir err: %s" % e)
    listing = eal.list_assets(dst_root, False, False)
    _log("mod root now (%d): %s" % (len(listing), [str(x) for x in listing]))
    _log("---- relocate done. Reopen via RunDevKit.bat and Build Mod. ----")


def corefill():
    """Same-path override prep: write the 120-level data straight into the CORE
    tables (internal package name stays the core path) so a pak built from these
    uassets overrides vanilla at mount. Logs each core uasset's on-disk path."""
    _engine_info()
    for core, _vanilla_csv, ext_csv in TABLES:
        name = core.split("/")[-1]
        n = _fill(core, ext_csv)
        _log("corefill %s -> %d rows (pkg %s)" % (name, n, core))
    _log("---- corefill done. Core tables now 120 rows; pack their .uasset at "
         "the core path to override. ----")


def _fill(path, csvf):
    t = unreal.load_asset(path)
    with open(csvf, "r", encoding="utf-8") as f:
        unreal.DataTableFunctionLibrary.fill_data_table_from_csv_string(t, f.read())
    unreal.EditorAssetLibrary.save_asset(path)
    return len(unreal.DataTableFunctionLibrary.get_data_table_row_names(t))


def apply():
    """Build the level mod as MOD-OWNED assets: duplicate each core leveling
    table into the mod's Content folder and fill it to 120 levels there (so
    Build Mod detects modded files). Also restore the core tables to vanilla,
    undoing the earlier in-place edits."""
    _engine_info()
    eal = unreal.EditorAssetLibrary
    for core, vanilla_csv, ext_csv in TABLES:
        name = core.split("/")[-1]
        # 1. restore core table to vanilla
        try:
            _log("restored core %s -> %d rows" % (name, _fill(core, vanilla_csv)))
        except Exception as e:
            _err("restore failed %s: %s" % (name, e))
        # 2. duplicate the vanilla core table into the mod folder
        modp = "%s/%s" % (MOD_ROOT, name)
        if eal.does_asset_exist(modp):
            eal.delete_asset(modp)
        if not eal.duplicate_asset(core, modp):
            _err("duplicate failed -> %s" % modp)
            continue
        # 3. fill the mod copy with the 120-level data
        _log("MOD asset %s -> %d rows at %s" % (name, _fill(modp, ext_csv), modp))
    # verify what now lives in the mod content folder
    try:
        listing = eal.list_assets(MOD_ROOT, True, False)
        _log("mod content (%d assets): %s" % (len(listing), [str(a) for a in listing]))
    except Exception as e:
        _err("list_assets failed: %s" % e)
    _log("---- apply done. Mod owns its 120-level tables now; Build Mod should detect them. ----")


if __name__ == "__main__":
    _log("MODE = %s" % MODE)
    try:
        if MODE == "discover":
            discover()
        elif MODE == "inspect":
            inspect()
        elif MODE == "dump":
            dump()
        elif MODE == "probe":
            probe()
        elif MODE == "override":
            override()
        elif MODE == "relocate":
            relocate()
        elif MODE == "verify":
            verify()
        elif MODE == "corefill":
            corefill()
        elif MODE == "makemc":
            makemc()
        elif MODE == "findmc":
            findmc()
        elif MODE == "mcprobe":
            mcprobe()
        elif MODE == "exinspect":
            exinspect()
        elif MODE == "apply":
            apply()
        else:
            raise SystemExit("Unknown CONAN_MOD_MODE: %s" % MODE)
    except SystemExit:
        raise
    except Exception:
        _err("UNCAUGHT:\n" + traceback.format_exc())
