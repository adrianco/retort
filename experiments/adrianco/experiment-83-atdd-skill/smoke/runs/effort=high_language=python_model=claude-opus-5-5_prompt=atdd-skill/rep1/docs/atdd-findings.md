# ATDD findings

Flight recorder of things the acceptance tests surfaced. One line per finding.

- 2026-10-01: `BR-Football-Dataset.csv` spells clubs "EC Bahia", "EC Juventude", "EC Vitoria"; unmatched, they double-counted ~400 Série A matches (2019 champion showed 93 pts instead of 90).
- 2026-10-01: `Brasileirao_Matches.csv` has 82 NA results: 81 are late-2022 fixtures not yet played when scraped (results exist in BR-Football), 1 is Chapecoense v Atlético-MG 2016, never played. `novo_campeonato_brasileiro.csv` records that one as 0-0.
- 2026-10-01: `BR-Football-Dataset.csv` tags a regional Brasília v CA Taguatinga match (2016-01-30) as "Serie A".
- 2026-10-01: Away goals must not decide finals: the 2015 Copa do Brasil final (Santos/Palmeiras, 2-2 agg.) went to penalties.
- 2026-10-01: "Guaraní (PAR)" was being merged with Guarani-SP; foreign country tags now take precedence over Brazilian aliases.
- 2026-10-01: FIFA 19 data has no Flamengo, Palmeiras, Corinthians or São Paulo squads, and its Brazilian-club players have licence-substitute names; questions about those squads honestly return none.
- 2026-10-01: `Libertadores_Matches.csv` has a placeholder 2022 final row (season "NA", score "-"); it is skipped.
