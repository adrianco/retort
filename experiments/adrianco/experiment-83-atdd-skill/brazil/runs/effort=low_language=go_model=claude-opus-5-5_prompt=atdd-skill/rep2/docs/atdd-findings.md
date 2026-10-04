# ATDD findings

- 2026-10-03: Copa do Brasil "final" spec exposed that BR-Football-Dataset rows have no round info; they were leaking into final-stage queries. Fixed by only treating a match as a final when its season's round data is known.
- 2026-10-03: Brasileirão/Copa seasons overlap across three CSVs with differing team spellings and dates; de-duplication is by competition+season source priority (Brasileirao_Matches > novo_campeonato > BR-Football) rather than per-match keys.
- 2026-10-03: FIFA dataset contains no Brazilian-club players (e.g. Flamengo); club queries answer "No players found" explicitly.
