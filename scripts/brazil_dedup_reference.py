#!/usr/bin/env python3
"""Ground truth for how many DISTINCT matches the brazil corpus actually holds.

WHY. Every brazil implementation reports how much it loaded, and those numbers
disagree — python 23,954, go 16,947 — while both score 12/12. Without a
reference the comparison is unreadable: is 16,947 a loader that dropped a file,
or a loader that correctly merged the overlap? The five match files cover
overlapping year ranges (BR-Football 2014-2023, Brasileirao_Matches 2012-2022,
novo_campeonato 2003-2019), so the same fixture appears 2-3 times and the honest
total is neither the sum nor any single file.

This computes the sum and several dedup keys from the CSVs themselves, so a run's
self-reported count can be classified rather than guessed at:

    ~= sum          -> no dedup; double-counts (the 12/12-but-wrong case)
    ~= unique key   -> merged the overlap; the numbers it answers with are sound
    << unique       -> dropped data

Usage:  python scripts/brazil_dedup_reference.py <dir-with-data/kaggle>
"""
from __future__ import annotations

import csv
import sys
import unicodedata
from pathlib import Path

#: (filename, date-col, home-col, away-col) per schema family. Three different
#: shapes, which is a large part of why implementations diverge here at all.
FILES = [
    ("Brasileirao_Matches.csv", "datetime", "home_team", "away_team"),
    ("Brazilian_Cup_Matches.csv", "datetime", "home_team", "away_team"),
    ("Libertadores_Matches.csv", "datetime", "home_team", "away_team"),
    ("BR-Football-Dataset.csv", "date", "home", "away"),
    ("novo_campeonato_brasileiro.csv", "Data", "Equipe_mandante", "Equipe_visitante"),
]


def norm(s: str) -> str:
    """Accent/case/state-suffix-insensitive team key ('Sao Paulo-SP' == 'São Paulo')."""
    t = unicodedata.normalize("NFKD", (s or "").strip())
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    for suf in ("-sp", "-rj", "-mg", "-rs", "-pr", "-sc", "-ba", "-pe", "-ce", "-go"):
        if t.endswith(suf):
            t = t[: -len(suf)]
    return t.strip()


def daykey(s: str) -> str:
    """Just the date part, across DD/MM/YYYY and ISO-ish formats."""
    s = (s or "").strip()
    if "/" in s[:10]:
        parts = s[:10].split("/")
        if len(parts) == 3:
            d, m, y = parts
            return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
    return s[:10]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".") / "data" / "kaggle"
    if not root.is_dir():
        print(f"no data/kaggle under {root.parent}", file=sys.stderr)
        return 1

    total = 0
    by_file: dict[str, int] = {}
    exact: set[tuple] = set()          # date + both teams
    loose: set[tuple] = set()          # date + unordered team pair (venue-agnostic)

    for fname, dcol, hcol, acol in FILES:
        p = root / fname
        if not p.exists():
            print(f"  MISSING {fname}", file=sys.stderr)
            continue
        n = 0
        with p.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                h, a = norm(row.get(hcol, "")), norm(row.get(acol, ""))
                if not h or not a:
                    continue
                d = daykey(row.get(dcol, ""))
                n += 1
                exact.add((d, h, a))
                loose.add((d, *sorted((h, a))))
        by_file[fname] = n
        total += n

    print("## Brazil corpus — how many matches are actually distinct\n")
    for f, n in by_file.items():
        print(f"  {f:34s} {n:6,}")
    print(f"\n  SUM of files (no dedup)          {total:6,}")
    print(f"  distinct (date + home + away)    {len(exact):6,}")
    print(f"  distinct (date + team pair)      {len(loose):6,}")
    dupes = total - len(exact)
    print(f"\n  duplicate rows across files:     {dupes:6,} "
          f"({dupes / total * 100:.0f}% of the sum)")
    print("\nRead a run's self-reported load against these:")
    print(f"  ~{total:,}  -> no dedup; it double-counts (still scores 12/12)")
    print(f"  ~{len(exact):,}  -> merged the overlap; its answers are sound")
    print(f"  <<{len(exact):,} -> dropped data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
