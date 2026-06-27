# Offline generator: extend the 3 vanilla progression tables 60 -> 120 levels.
# Reads the dumped vanilla CSVs, KEEPS rows 1..60 (0..59 for attr) EXACTLY,
# APPENDS calibrated rows continuing vanilla's own pattern. No editor needed.
import csv, os

EXP = r"D:\tmp\conan_export"
CAP = 120

def read(name):
    with open(os.path.join(EXP, name), newline="") as f:
        rows = list(csv.reader(f))
    return rows[0], rows[1:]

def write(name, header, rows):
    out = os.path.join(EXP, name)
    with open(out, "w", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        w.writerows(rows)
    return out

# ---- XP table (rows 1..60, cumulative LevelStart/LevelEnd) -> 1..120 ----------
h_xp, xp = read("DT_ExperienceSystemLevel.csv")
xp = [[int(r[0]), int(r[1]), int(r[2])] for r in xp]
# continue per-level delta with second-difference 175 (vanilla avg near L60)
prev_delta = xp[-1][2] - xp[-1][1]          # delta(60)=359500
prev_dd    = prev_delta - (xp[-2][2]-xp[-2][1])  # dd(60)=11300
level_end  = xp[-1][2]                       # 7619025
new_xp = [[str(l), str(s), str(e)] for l, s, e in xp]   # keep 1..60 exactly (as strings)
for L in range(61, CAP + 1):
    prev_dd += 175
    prev_delta += prev_dd
    start = level_end
    level_end = start + prev_delta
    new_xp.append([str(L), str(start), str(level_end)])
write("DT_ExperienceSystemLevel.120.csv", h_xp, new_xp)

# ---- Attribute table (rows 0..59) -> 0..119 ----------------------------------
h_at, at = read("DT_AttributeSystem.csv")
new_at = [list(r) for r in at]              # keep 0..59 exactly
for row in range(60, CAP):                  # 0-indexed: levels up to 120 -> rows 0..119
    cost = 6 + (row - 25) // 5              # continue +1 per 5 (row55..59=12 -> row60+=13..)
    new_at.append([str(row), str(cost), "1"])
write("DT_AttributeSystem.120.csv", h_at, new_at)

# ---- Feats table (rows 1..60) -> 1..120 -------------------------------------
h_ft, ft = read("DT_FeatsPerLevel.csv")
new_ft = [list(r) for r in ft]             # keep 1..60 exactly
def feat_points(L):
    if L % 10 == 0:
        return 9 + 6 * (L // 10 - 1)       # decade milestone: L60=39, L70=45...
    k = (L - 1) // 10
    p = ((L - 1) % 10) + 1
    return (2 * k + 1) if p <= 4 else (2 * k + 2)
for L in range(61, CAP + 1):
    new_ft.append([str(L), str(feat_points(L))])
write("DT_FeatsPerLevel.120.csv", h_ft, new_ft)

# ---- verify / show ----------------------------------------------------------
print("XP   rows:", len(new_xp), "| L60:", new_xp[59], "| L61:", new_xp[60], "| L120:", new_xp[-1])
print("ATTR rows:", len(new_at), "| r59:", new_at[59], "| r60:", new_at[60], "| r119:", new_at[-1])
print("FEAT rows:", len(new_ft), "| L60:", new_ft[59], "| L61:", new_ft[60],
      "| L70:", new_ft[69], "| L120:", new_ft[-1])
xp_l60_end = int(new_xp[59][2]); xp_l120_end = int(new_xp[-1][2])
print("XP cumulative: L60 end =", xp_l60_end, "-> L120 end =", xp_l120_end)
