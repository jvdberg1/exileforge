#!/usr/bin/env python3
# ExileForge -- runs INSIDE the Conan Dev Kit editor (via UnrealEditor-Cmd
# -run=pythonscript), driven by exileforge.ps1. Configured by env vars:
#   EF_MOD     = mod name
#   EF_WORKDIR = scratch folder for CSVs
#   EF_MODE    = "dump"  -> export the 3 vanilla progression tables to EF_WORKDIR
#                "override" -> restore core to vanilla, then duplicate each table
#                into /Game/Mods/<EF_MOD>/Content/Systems/Progression/<name> and
#                fill it from <name>.ext.csv (the overlay override).
import os

try:
    import unreal
except ImportError:
    raise SystemExit("run via UnrealEditor-Cmd.exe (see exileforge.ps1)")

MOD = os.environ["EF_MOD"]
WORK = os.environ["EF_WORKDIR"]
MODE = os.environ.get("EF_MODE", "dump")
DTL = unreal.DataTableFunctionLibrary
EAL = unreal.EditorAssetLibrary
CORE = [
    "/Game/Systems/Progression/DT_ExperienceSystemLevel",
    "/Game/Systems/Progression/DT_AttributeSystem",
    "/Game/Systems/Progression/DT_FeatsPerLevel",
]


def log(m):
    unreal.log("[ExileForge] " + str(m))


def dump():
    if not os.path.isdir(WORK):
        os.makedirs(WORK)
    for c in CORE:
        name = c.split("/")[-1]
        DTL.export_data_table_to_csv_file(unreal.load_asset(c),
                                          os.path.join(WORK, name + ".csv"))
        log("dumped " + name)


def fill(path, csvf):
    t = unreal.load_asset(path)
    with open(csvf, "r", encoding="utf-8") as f:
        DTL.fill_data_table_from_csv_string(t, f.read())
    EAL.save_asset(path)
    return len(DTL.get_data_table_row_names(t))


def override():
    for c in CORE:
        name = c.split("/")[-1]
        # keep the base game clean: restore core to the vanilla dump
        fill(c, os.path.join(WORK, name + ".csv"))
        dst = "/Game/Mods/%s/Content/Systems/Progression/%s" % (MOD, name)
        if EAL.does_asset_exist(dst):
            EAL.delete_asset(dst)
        if not EAL.duplicate_asset(c, dst):
            unreal.log_error("[ExileForge] duplicate failed -> " + dst)
            continue
        log("override %s -> %d rows at %s" % (name, fill(dst, os.path.join(WORK, name + ".ext.csv")), dst))


log("MODE=%s MOD=%s WORK=%s" % (MODE, MOD, WORK))
if MODE == "dump":
    dump()
elif MODE == "override":
    override()
else:
    raise SystemExit("unknown EF_MODE: " + MODE)
log("ef_editor done (" + MODE + ")")
