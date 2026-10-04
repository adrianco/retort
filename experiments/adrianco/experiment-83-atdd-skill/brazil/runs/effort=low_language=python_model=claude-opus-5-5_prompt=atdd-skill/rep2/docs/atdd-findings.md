# ATDD findings

- 2026-10-03: Brasileirao_Matches.csv 2022 has unplayed fixtures with NA scores (rounds 31+); 2022 aggregates are partial. Spec moved to 2019.
- 2026-10-03: Match files overlap (Serie A/Copa do Brasil in several files); server uses one source per competition+season to avoid double counting.
