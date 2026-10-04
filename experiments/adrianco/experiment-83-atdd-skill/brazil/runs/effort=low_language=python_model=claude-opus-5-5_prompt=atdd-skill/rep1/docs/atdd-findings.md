# ATDD findings

- 2026-10-03: Brasileirao_Matches.csv has only 299 of 380 matches for 2022; merged with BR-Football-Dataset.csv (deduped per season/home/away).
- 2026-10-03: BR-Football-Dataset.csv dates the 2020 season's Jan–Feb 2021 games as 2021; season inferred as year-1 for Jan–Feb league games.
- 2026-10-03: Stage filter "final" matched "semifinals"/"quarterfinals"; now exact match.
- 2026-10-03: No Libertadores 2021 final in the dataset; FIFA data has no Flamengo/Palmeiras/Corinthians squads (licensing).
- 2026-10-03: "Atletico", "America", "Botafogo" are ambiguous without state suffix; canonical names keep the state.
