# ATDD findings

Things the acceptance-test work surfaced that are not visible in the code itself. One line each, dated.

- 2026-10-03: Spec error: three specs recorded different results for the same Brasileirão home fixture in the same season from different datasets. That can't happen in a league, and the system correctly merged them into one match. Fixed the specs (distinct seasons), not the code.
- 2026-10-03: Data: BR-Football-Dataset.csv disagrees with both primary Brasileirão files on some scores (e.g. 2014-11-23 Sport 2-2 Fluminense recorded as 2-1). Duplicates now merge by fixture and season/date regardless of score; the primary files' score wins.
- 2026-10-03: Data: BR-Football-Dataset.csv contains same-fixture duplicate rows one day apart (e.g. Atlético-MG 3-2 Santos on 2014-09-24 and 2014-09-25). Same result in the same dataset within 3 days is treated as one match.
- 2026-10-03: Data: Brasileirao_Matches.csv has 82 rows with NA goals (mostly late 2022). Those results come only from the extended dataset; the rows are skipped and counted in dataset_summary.
- 2026-10-03: Data: Copa do Brasil rounds are numbers whose meaning varies by season (the final is round 6, 7 or 8). The final is derived as the season's last round when it is a single tie; 2021 has no final in the data.
- 2026-10-03: Data: FIFA 19 has no Flamengo, Palmeiras, São Paulo or Corinthians squads, and Brazilian-league players have licence-generated names. Player questions about those clubs honestly return no players. The cross-file spec uses Grêmio, which is present.
- 2026-10-03: Naive name-based club merging wrongly joined clubs from different states (São José-PA/-RS, River-AC/-PI). Clubs are only unified when their states agree and, for same-day matching, their names share a significant word.
