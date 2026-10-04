# ATDD findings

Things the acceptance-test work surfaced, newest first.

- 2026-10-04: The spec "derbies played in 2022 include the Grenal" was wrong. Grêmio was in Série B in 2022. The spec now uses 2023. Real-data specs only assert facts checked independently of the code.
- 2026-10-04: The brief's example "Who is Gabriel Barbosa?" has no answer in FIFA 19. He is not in the file. The spec now requires a "not found" answer that suggests similar names, rather than an error.
- 2026-10-04: FIFA 19 has no squads for Flamengo, Palmeiras, Corinthians or São Paulo, so the brief's example "highest-rated players at Flamengo" can only answer "none found". The specs use Cruzeiro, Santos and Grêmio instead.
- 2026-10-04: Club search by name failed when the club had players but no matches ("Sao Paulo FC" with only FIFA data). Club names now resolve through team identity first. This was found by the "forwards at a club" spec.
- 2026-10-04: Série A matches appear in up to three files (`Brasileirao_Matches`, `novo_campeonato_brasileiro`, `BR-Football-Dataset`). Without cross-file merging, standings would double count. The spec "count a match once even when several datasets record it" protects this.
- 2026-10-04: The 2020 Brasileirão ran until February 2021. The `BR-Football-Dataset` has no season column, so January–March league matches are assigned to the previous season. The spec "pandemic-delayed 2020 season" (Flamengo 71 pts) protects this.
- 2026-10-04: `Libertadores_Matches.csv` has one unplayed row (`NA` date, `-` goals). It is counted as a record but not as a match.
