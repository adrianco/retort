# Brazilian Soccer MCP with spec and basic data sets

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in Go, that lets an LLM answer natural-language questions about Brazilian soccer: matches, team records, league tables, competition statistics and FIFA player ratings. The server uses only the Go standard library and speaks newline-delimited JSON-RPC over stdio.

## Specification
brazilian-soccer-mcp-guide.md

## Build, test and run

```sh
go build -o brazilian-soccer-mcp .
go test ./...                  # unit tests plus integration tests against data/kaggle
./brazilian-soccer-mcp -data data/kaggle
```

The server loads the six CSV files at startup (about 0.1 s), then answers requests on stdin/stdout. Log lines go to stderr.

To connect it to an MCP client, register the binary as a stdio server, for example in a client config:

```json
{ "mcpServers": { "brazilian-soccer": { "command": "/path/to/brazilian-soccer-mcp", "args": ["-data", "/path/to/data/kaggle"] } } }
```

## Tools

| Tool | Answers |
|------|---------|
| `find_matches` | Matches by team, opponent (head-to-head), venue, competition, season, date range, round, or finals only. Newest first. |
| `team_stats` | W/D/L, goals for and against, and win rate for a team, optionally by venue, competition, season or date range. |
| `team_ranking` | Teams ranked by win rate, for example the best home record in a season. |
| `standings` | League table calculated from results (points, goal difference, champion). Defaults to the latest season. |
| `competition_stats` | Matches, goals per match, home/draw/away rates, and the biggest wins. |
| `search_players` | FIFA players by name, nationality, club, position (or group such as `forward`) and minimum rating. |
| `brazilian_clubs_summary` | Top-rated Brazilian players, and Brazilian players per Brazilian club with average rating. |

## Data sources

Kaggle data can't be downloaded without an account so these (freely available with attribution) data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv
- data/kaggle/Brazilian_Cup_Matches.csv
- data/kaggle/Libertadores_Matches.csv

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv

## How the data is reconciled

- **Team names.** The files spell clubs differently: `Palmeiras-SP`, `Palmeiras - SP`, `Atletico Mineiro`, `Sport Club Corinthians Paulista`, `Red Bull Bragantino`. Names are folded (accents removed, lower-cased, punctuation dropped), state codes are separated out, generic club words such as `EC` and `FC` are removed, and a small alias table maps the long-form names (`normalize.go`). Clubs that share a base name, such as Atlético-MG, Atlético-PR and Atlético-GO, get state-qualified IDs. A name without a state joins the club it is most often seen with.
- **Overlapping files.** The Brasileirão files overlap for 2012–2019, and BR-Football overlaps for 2014–2023. Each (competition, season) comes from the first file that covers it, in the order Brasileirão → Cup → Libertadores → Historical → BR-Football. Later files only fill seasons no earlier file has (`data.go`).
- **Dates** are accepted as `YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS` and `DD/MM/YYYY`. Seasons come from each file's own season column, because Brazilian seasons can run into the next calendar year.
- **Finals.** Copa do Brasil finals are inferred as the highest numbered round in each season, and Libertadores finals come from the `stage` column.
- **Brazilian clubs.** FIFA club names are matched against clubs seen in domestic competitions, with generic words removed. The whole name must match, so `Santos Laguna` and `Vitória Guimarães` are excluded.

## Known limitations

- **Incomplete source data.** The 2022 Brasileirão file has 81 fixtures with `NA` scores (not yet played in that snapshot). These are skipped, so the 2022 table is partial. The BR-Football 2023 Serie A is missing a few matches, so the 2023 table is one or two games short for some clubs.
- **Relegation** is not calculated. The standings tool shows the table and the champion only.
- **Top scorers** are not in the data.
- **Cup finals** are inferred from the last round number, and the 2020 season has no real final in the file.
- **FIFA coverage.** The FIFA file has no Brazilian Serie A squads, so `search_players` with `club: Flamengo` returns nothing. It does contain Brazilian nationals at foreign clubs and some Brazilian clubs (Grêmio, Cruzeiro, …), and `brazilian_clubs_summary` reports those. Players not in the file, such as Gabriel Barbosa, return "No players found."
- **Stateless names.** A club name with no state that matches several clubs goes to the club it is most often seen with. Two clubs with the same name in different states can be mixed up in that case.

## Tests

The tests use BDD-style scenarios (`Scenario:` subtests with Given/When/Then comments). They are split by layer:

- `normalize_test.go`: name, accent and date parsing.
- `store_test.go`: loading all sources, de-duplication, team identity, finals.
- `queries_test.go`: match, team, standings, competition and player queries through the tool layer, using hand-checked fixtures (`fixtures_test.go`).
- `mcp_test.go`: JSON-RPC protocol behaviour (initialize, tools/list, notifications, errors).
- `integration_test.go`: runs against the real CSVs. It checks that all six files load in under 5 s, that the 2019 table matches the published result (Flamengo 90 pts, 28W 6D 4L), and that the sample questions from the spec answer. It is skipped when `data/kaggle` is missing.
