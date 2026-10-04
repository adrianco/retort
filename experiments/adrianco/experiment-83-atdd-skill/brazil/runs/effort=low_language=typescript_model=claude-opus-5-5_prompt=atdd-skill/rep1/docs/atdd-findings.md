# ATDD findings

- 2026-10-03: Brasileirao_Matches.csv has NA scores for 81 unplayed 2022 fixtures; league tables now fill these gaps from the other Serie A sources (same season + home + away).
- 2026-10-03: Spec assumed Alisson was the top Brazilian GK; the FIFA data ranks Ederson (86) first. Corrected the spec to match the data.
- 2026-10-03: The match sources overlap (2012-2019 Brasileirão appears in two files); matches are deduplicated on date + normalised teams, and each season's table uses one preferred source.
