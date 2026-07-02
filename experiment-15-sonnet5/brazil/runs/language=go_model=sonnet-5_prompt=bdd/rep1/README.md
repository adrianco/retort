# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Data Sources
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

## Implementation

A Go MCP server (`brazilian-soccer-mcp`) implementing the spec in `TASK.md`. It loads all
six CSV files into memory at startup and exposes them as MCP tools over the standard
newline-delimited JSON-RPC 2.0 stdio transport (`initialize`, `tools/list`, `tools/call`).

No external dependencies - only the Go standard library (`encoding/csv`, `encoding/json`,
`regexp`, etc). Build and run:

```
go build -o brazilian-soccer-mcp .
./brazilian-soccer-mcp --data-dir data/kaggle
```

Run the test suite (BDD-style: `Test_GivenX_WhenY_ThenZ`, one behaviour per test):

```
go test ./...
```

### Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season |
| `head_to_head` | Full match history and win/draw/goal tally between two teams |
| `team_record` | A team's win/draw/loss record, optionally by season/competition/venue |
| `standings` | League table calculated from match results, with champion/relegation flags |
| `search_players` | Search FIFA player data by name, nationality, club, position, rating |
| `top_players` | Highest-rated players, optionally filtered |
| `team_players` | FIFA squad for a club, cross-referencing match-data team names |
| `biggest_wins` | Largest victories by goal difference |
| `stats_summary` | Average goals/match, home/away/draw win rates, biggest win |
| `best_record` | Teams ranked by win rate for a given venue/competition/season |

### Key design points

- **Team name normalization** (`normalize.go`): strips accents, parenthetical notes, and
  decorative state suffixes (`Palmeiras-SP` -> `Palmeiras`), with a curated alias table for
  ~35 major clubs so that differently-spelled or differently-sourced records collapse to one
  canonical identity. Clubs whose real identity embeds a state code (`Atletico-MG` vs
  `Atletico-PR` vs `Atletico-GO` are three different clubs) are matched against the alias
  table *before* suffix stripping, so they aren't incorrectly merged or truncated.
- **Cross-source deduplication** (`loader.go`): `Brasileirao_Matches.csv`,
  `novo_campeonato_brasileiro.csv`, and `BR-Football-Dataset.csv` (as "Serie A") all cover
  overlapping real Brasileirao seasons (roughly 2012-2019). Without deduplication, standings
  and records would double- or triple-count those seasons. Matches are deduplicated by
  (competition, season, home team, away team, score) once all files are loaded, keeping the
  first (most purpose-built) source. This was verified against a known real result: the 2019
  Brasileirao standings now correctly show Flamengo as champion with 90 points from 38
  matches (28W-6D-4L), matching the historical record.
- **Flexible date parsing** (`dateparse.go`): handles ISO date+time, ISO date-only, and
  Brazilian `DD/MM/YYYY` formats across the different files.
- **Known limitation**: for clubs *outside* the curated alias table, two lower-tier clubs
  that share a base name but play in different states (e.g. a minor "Botafogo" from a state
  other than Rio de Janeiro) may still collapse together once an unrecognized state suffix is
  stripped. This is an inherent ambiguity in the source data's naming conventions.
- The FIFA player dataset (`fifa_data.csv`, sourced from FIFA 19) does not include every
  major Brasileirao club's roster (e.g. Flamengo, Corinthians, Palmeiras, Sao Paulo, and
  Vasco da Gama are absent) - a licensing limitation of that era's game, not a bug in this
  server. `team_players`/`search_players` correctly return "no players found" for those clubs.
