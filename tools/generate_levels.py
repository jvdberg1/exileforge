#!/usr/bin/env python3
# Generates the level-progression table for Example Tweaks.
# Builds rows 61..MAX_LEVEL so the mod can cap at SERVER_CAP now and raise it later by 1 line.
# XP model is a smooth continuation; it gets CALIBRATED to the real lvl1-60 table once exported.
import csv
MAX_LEVEL   = 291   # build capacity to 291
SERVER_CAP  = 120   # what our server actually allows
BASE_L60_XP = 200000  # placeholder per-level XP at L60 (recalibrate to real export)

def xp_to_next(L):
    # gentle quadratic growth past 60 so late levels feel earned but not insane
    return int(round(BASE_L60_XP * (1 + (L-60)*0.06) ** 2))

def attr_points(L):   # +1 attribute point per level past 60 (MoreLevelsPls-style)
    return 1 if L > 60 else 0

def feat_points(L):   # +12 knowledge per level, +40 every 10th (milestone)
    return 52 if L % 10 == 0 else 12

rows=[]
for L in range(61, MAX_LEVEL+1):
    rows.append({
        "Level": L,
        "XP_To_Next": xp_to_next(L),
        "Attribute_Points": attr_points(L),
        "Feat_Points": feat_points(L),
        "Within_Server_Cap": "Y" if L <= SERVER_CAP else "n",
    })

with open("data/levels.csv","w",newline="") as f:
    w=csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

cap_rows=[r for r in rows if r["Within_Server_Cap"]=="Y"]
tot_attr=sum(r["Attribute_Points"] for r in cap_rows)
tot_feat=sum(r["Feat_Points"] for r in cap_rows)
print(f"wrote data/levels.csv: {len(rows)} rows (61..{MAX_LEVEL})")
print(f"server cap {SERVER_CAP}: +{tot_attr} attribute pts, +{tot_feat} feat pts gained over 60->{SERVER_CAP}")
print("sample:")
for r in rows[:3]+rows[57:60]: print("  ", r)
