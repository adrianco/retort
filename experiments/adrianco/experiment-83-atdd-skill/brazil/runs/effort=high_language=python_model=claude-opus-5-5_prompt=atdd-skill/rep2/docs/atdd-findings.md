# ATDD findings log

Things that writing executable specifications surfaced. One line per finding.

## 2026-10-03

- Spec assumption wrong: Flamengo and Fluminense never met in the Libertadores 2013-2022; they did meet in the 2023 Copa do Brasil (extended dataset). Spec corrected.
- Gabriel Barbosa (TASK.md sample question) is not in the FIFA 19 data; `player_profile` now answers "not in the dataset" with similar names instead of erroring.
- FIFA 19 has no licence for most Brazilian clubs: Flamengo, Palmeiras, São Paulo, Corinthians and Vasco are absent, and players at the licensed Brazilian clubs have generated names (e.g. "Louri Beretta" at Atlético-MG).
- novo_campeonato_brasileiro.csv state columns are wrong for some clubs (Bahia "BH", Vitória "ES"), which split clubs in two and left 2012-2017 Série A seasons with up to 440 matches. The state columns are now ignored; seasons are 380.
- BR-Football-Dataset.csv labels some 2014 Copa do Brasil ties as "Serie A" (e.g. Atlético-MG 3-2 Santos, 2014-09-24). A second meeting of a league pairing in one season from a secondary dataset is now discarded (4 records).
- BR-Football-Dataset.csv has a stray regional match (Brasília vs CA Taguatinga, 2016-01-30) tagged Série A; teams with under half the matches of the busiest team are left out of league tables.
- Brazilian_Cup_Matches.csv 2021 stops at round 4 with unplayed fixtures ("NA" scores); unplayed fixtures are ignored and no final is inferred for incomplete seasons. 2022-2023 Copa do Brasil (extended dataset only) has no round numbers, so their finals can't be identified.
- Libertadores_Matches.csv has one unplayed final with season "NA" and "-" scores; ignored.
- The tie-break spec originally passed with goal difference removed (goals scored decided it too); spec tightened so goal difference alone decides.
- "Premier League" resolved to Série A because "league" matched anywhere in the question; only distinctive competition names now match inside a phrase.
