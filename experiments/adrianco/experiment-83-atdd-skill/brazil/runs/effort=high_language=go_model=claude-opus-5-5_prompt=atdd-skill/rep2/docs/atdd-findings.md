# ATDD findings

What writing executable specifications surfaced while building this system. One line per finding.

## 2026-10-03

- `Brasileirao_Matches.csv` has 82 rows with `NA` scores (mostly rounds 29-38 of 2022, plus one 2016 match); `BR-Football-Dataset.csv` has those results. The merge now fills the score from the other record (spec: `ShouldTakeAMissingScoreFromAnotherRecordOfTheSameMatch`).
- `novo_campeonato_brasileiro.csv` records Vitória's home state as `ES` (the stadium, Barradão, is in Salvador, BA). As a result Vitória was split into two clubs. The archive's state columns are now ignored and clubs are identified by name.
- `novo_campeonato_brasileiro.csv` lists Botafogo-RJ at home to Flamengo twice in 2009. Within one file, the "one home/away pairing per Série A season" rule is not applied.
- `BR-Football-Dataset.csv` contains duplicate rows of the same match a day apart (e.g. Goiás 2-3 Atlético-MG on both 2014-09-17 and 2014-09-18). Records within three days of each other are merged even when they come from the same file.
- `BR-Football-Dataset.csv` labels a Brasília v Taguatinga match (2016-01-30) as "Serie A". Série A rows found only in that file, between clubs absent from that season in the other files, are dropped.
- Two of my own specs recorded the same Série A home/away pairing twice in one season from different files. The system rightly merged them; the specs were impossible fixtures and were corrected. Synthetic data has to respect domain rules too.
- The Copa do Brasil 2021 data stops at the round of 16 (scores `NA`). Treating "highest round = final" mislabelled those matches as finals, so a round counts as the final only when it is a single tie.
- FIFA 19 does not license most Brazilian clubs (no Flamengo, Palmeiras, Corinthians or São Paulo), and the licensed ones (e.g. Santos, Grêmio) carry made-up player names. Gabriel Barbosa is not in the ratings. Player answers explain this rather than coming back empty.
- "Club América" (Mexico) was being linked to América-MG because "Club" was stripped as filler. Leading "Club"/"Clube" is no longer stripped.
- In the provided-data suite, five answers were checked against values computed independently in Python, not against the system's own output: Corinthians 2022 home record, Palmeiras-Santos head-to-head, Flamengo-Corinthians last meeting, 2019 table and 2020 relegation.
