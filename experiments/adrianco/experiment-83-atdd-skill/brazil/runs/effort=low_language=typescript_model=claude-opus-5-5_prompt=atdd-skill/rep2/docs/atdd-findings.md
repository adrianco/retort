# ATDD findings

- 2026-10-04: Brasileirão fixtures appear in 3 files with differing dates; de-dupe by season+home+away (date-based de-dupe double-counted, 2019 champion showed 124 pts).
- 2026-10-04: Brasileirao_Matches.csv 2022 is incomplete; BR-Football-Dataset.csv fills the gap once "EC Juventude"-style prefixes are normalised.
- 2026-10-04: "Corinthians home record 2022" spec was ambiguous — it means Brasileirão only; spec now states competition.
- 2026-10-04: State suffix "-SC" collided with "SC" club suffix (Avaí-SC split into two teams).
