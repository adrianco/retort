# ATDD findings

Things the acceptance specs revealed while building the system. One line per finding.

- 2026-10-03: The DSL defaulted match dates one day apart, so two Flamengo home games against Fluminense fell inside the server's 3-day cross-source duplicate window and merged. Fixed in the DSL: unrealistic synthetic data. Defaults are now a week apart.
- 2026-10-03: A Copa do Brasil spec gave its semi-final no date, so it defaulted into a different season and became that season's "final". The spec was wrong, not the system.
- 2026-10-03: The provided 2023 Série A data stops 3 matches short (377/380). The server named Grêmio champion; Palmeiras actually won. Added a spec: incomplete full-size seasons are provisional and name no champion.
- 2026-10-03: The Série A (82), Copa do Brasil (16) and Libertadores (2) files contain rows with no result (`NA`/`-`): unplayed or abandoned matches such as Chapecoense v Atlético-MG, 2016. They are skipped and reported.
- 2026-10-03: Portugal's "Boavista FC" (FIFA data) normalised to the same key as Boavista-RJ (Copa do Brasil) and was counted as a Brazilian club. Added a spec; foreign namesakes are now excluded.
- 2026-10-03: The acceptance package reaches the server only as a subprocess, so `go test` cached stale greens after server changes. The suite now blank-imports `internal/app` to tie the cache to the server code.
- 2026-10-03: FIFA 19 data has no Flamengo, Palmeiras, São Paulo or Corinthians squads (licensing), and its Brazilian-club squads use fictional names. The sample questions about those squads were answered with Grêmio and Santos instead.
