# ATDD findings log

Things the acceptance-test work surfaced that nobody was looking for. One line per finding.

- 2026-10-03 — `novo_campeonato_brasileiro.csv` UF columns are wrong for some clubs (Vitória home games tagged `ES`, Bahia tagged `BH`); appending them split clubs in two and broke cross-dataset de-duplication (2012 teams showed 40 matches). Names already carry needed suffixes, so UF is now ignored. Spec: "should list a match only once when several datasets record it".
- 2026-10-03 — `BR-Football-Dataset.csv` 2023 Serie A is missing 3 matches, so a calculated "champion" (Grêmio) would be wrong (Palmeiras won). Standings now report incomplete seasons as provisional, with no champion. Spec: "should warn that a season is incomplete rather than crown a champion".
- 2026-10-03 — `BR-Football-Dataset.csv` contains a regional match (Brasília v CA Taguatinga) labelled Serie A 2016. League tables now ignore teams that barely appear. Spec: "should leave a stray one-off match out of the league table".
- 2026-10-03 — A bare "River Plate" (Argentina, Libertadores) was being merged with River Plate-SE (Copa do Brasil) by state inference. International records now only inherit a Brazilian state from top-flight clubs. Spec: "should not confuse a foreign club with a Brazilian club of the same name".
- 2026-10-03 — BR-Football kick-off times look like UTC (e.g. 00:30 on 2021-02-26 for a 21:30 local match on 2021-02-25), so its dates can be a day late; de-duplication tolerates ±3 days.
- 2026-10-03 — FIFA 19 uses invented names for unlicensed Brazilian-club players (e.g. "Louri Beretta" at Atlético Mineiro); answers reflect the data as given. Flamengo, Palmeiras, Corinthians, São Paulo and Vasco have no squads in it.
- 2026-10-03 — "Gabriel Barbosa" (TASK sample question) is not in the FIFA data; the system says so and suggests similar names.
