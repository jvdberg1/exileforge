#!/usr/bin/env python3
# ExileForge -- extend the 3 vanilla progression tables to a level cap.
# Standalone; run with any Python (e.g. the Dev Kit's bundled python.exe).
#
#   python ef_levels.py <workdir> <cap>
#
# Reads vanilla dumps written by ef_editor.py (mode=dump) in <workdir>:
#   DT_ExperienceSystemLevel.csv  DT_AttributeSystem.csv  DT_FeatsPerLevel.csv
# Writes extended tables (vanilla rows preserved, continued to <cap>):
#   *.ext.csv
import sys
import os
import csv


def read(p):
    with open(p, newline="") as f:
        r = list(csv.reader(f))
    return r[0], r[1:]


def write(p, header, rows):
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    if len(sys.argv) < 3:
        print("usage: ef_levels.py <workdir> <cap>")
        sys.exit(2)
    work = sys.argv[1]
    cap = int(sys.argv[2])

    # XP: cumulative LevelStart/LevelEnd, rows 1..60 -> 1..cap.
    # Continue the per-level delta with vanilla's ~constant 2nd difference (175).
    h, xp = read(os.path.join(work, "DT_ExperienceSystemLevel.csv"))
    xp = [[int(r[0]), int(r[1]), int(r[2])] for r in xp]
    delta = xp[-1][2] - xp[-1][1]
    dd = delta - (xp[-2][2] - xp[-2][1])
    end = xp[-1][2]
    out = [[str(l), str(s), str(e)] for l, s, e in xp]
    for L in range(len(xp) + 1, cap + 1):
        dd += 175
        delta += dd
        start = end
        end = start + delta
        out.append([str(L), str(start), str(end)])
    write(os.path.join(work, "DT_ExperienceSystemLevel.ext.csv"), h, out)

    # Attribute table: 0-indexed rows 0..59 -> 0..cap-1. RewardPerLevel=1; cost +1 per 5.
    h, at = read(os.path.join(work, "DT_AttributeSystem.csv"))
    out = [list(r) for r in at]
    for row in range(len(at), cap):
        cost = 6 + (row - 25) // 5
        out.append([str(row), str(cost), "1"])
    write(os.path.join(work, "DT_AttributeSystem.ext.csv"), h, out)

    # Feats table: rows 1..60 -> 1..cap. +1 per 5 levels; decade milestones 9+6k.
    h, ft = read(os.path.join(work, "DT_FeatsPerLevel.csv"))
    out = [list(r) for r in ft]

    def feat(L):
        if L % 10 == 0:
            return 9 + 6 * (L // 10 - 1)
        k = (L - 1) // 10
        p = ((L - 1) % 10) + 1
        return (2 * k + 1) if p <= 4 else (2 * k + 2)

    for L in range(len(ft) + 1, cap + 1):
        out.append([str(L), str(feat(L))])
    write(os.path.join(work, "DT_FeatsPerLevel.ext.csv"), h, out)

    print("ef_levels: extended XP/Attribute/Feats to cap %d in %s" % (cap, work))


if __name__ == "__main__":
    main()
