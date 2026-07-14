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

---

## Implementation

A Go implementation of the MCP server specified in `brazilian-soccer-mcp-guide.md` (== `TASK.md`), built test-first (TDD).

### Architecture

- `internal/soccer` — the knowledge graph itself, independent of MCP:
  - `normalize.go` — `NormalizeTeamKey` folds accents, strips Brazilian state (UF) suffixes (e.g. `Flamengo-RJ` → `flamengo`), strips punctuation, and resolves a small alias table (e.g. `Atlético Mineiro` / `Atlético-MG` → `atletico`) so the same club matches across datasets regardless of spelling.
  - `date.go` — `ParseDate` handles the three date formats present in the data (ISO with time, ISO date-only, `DD/MM/YYYY`).
  - `match.go` / `player.go` — CSV loaders for each of the 6 datasets, normalizing every record into a common `Match`/`Player` struct. Rows with unparseable dates (e.g. one corrupted `NA` row in `Libertadores_Matches.csv`) are skipped rather than failing the whole load.
  - `load.go` — `LoadStoreFromDir` loads all 6 files into a queryable `Store`.
  - `store.go` / `player_query.go` — the query engine: `FindMatches`, `HeadToHead`, `TeamRecord`, `Standings` (computed from match results), `BiggestWins`, `StatsSummary`, `SearchPlayers`.
- `internal/mcpserver` — exposes the `Store` as MCP tools (using the official `github.com/modelcontextprotocol/go-sdk`), with pure formatting functions (`format.go`) rendering results in the human-readable style shown in the spec's example answers.
- `cmd/server` — entry point; loads `data/kaggle` and runs the server over stdio.

### Tools exposed

| Tool | Purpose |
|------|---------|
| `find_matches` | Matches by team, opponent, competition, season, date range |
| `head_to_head` | Match history + win/draw record between two teams |
| `team_record` | A team's W/D/L and goals for/against, optionally by season/competition/venue |
| `standings` | Competition table for a season, computed from match results |
| `biggest_wins` | Most lopsided results, optionally scoped to competition/season |
| `stats_summary` | Average goals per match, home/away/draw win rates |
| `search_players` | FIFA player search by name/nationality/club/position/rating (also serves "top rated" queries) |

### Running

```
go build -o brserver ./cmd/server
./brserver -data-dir data/kaggle
```

The server speaks MCP over stdio and can be pointed at by any MCP-compatible client/LLM.

### Testing

```
go test ./...
```

Every unit is TDD'd (normalization, date parsing, each CSV loader, every query method, response formatting), plus an integration test that loads the real `data/kaggle` files and a smoke test that drives the MCP server end-to-end over an in-memory transport. Manual timing against the full dataset (23,953 matches, 18,207 players) shows queries completing in low single-digit milliseconds, well under the spec's 2s/5s targets.

### Known data-quality notes

- **Overlapping Brasileirão sources**: `Brasileirao_Matches.csv` (2012-2022) and `novo_campeonato_brasileiro.csv` (2003-2019) both cover 2012-2019, and `BR-Football-Dataset.csv` separately covers Serie A/B/C plus Copa do Brasil. These are intentionally tagged as distinct competitions (`Brasileirao`, `Brasileirao (Historical)`, `Serie A`, etc.) rather than merged, since deduplicating differently-formatted rows for the same real-world match is unreliable. A `find_matches` query with no competition filter will therefore show the same real match more than once, once per covering source — scope by `competition` for a single, non-duplicated view.
- **FIFA club coverage is uneven**: `fifa_data.csv` only includes players whose club was in that FIFA edition's licensed roster. Several major Brazilian clubs (e.g. Flamengo, Palmeiras, Corinthians, São Paulo, Vasco) are entirely absent as clubs in this dataset, while others (Santos, Fluminense, Botafogo, Grêmio, Internacional, Cruzeiro, Bahia, Atlético Mineiro) are present. `search_players` correctly returns no results for an absent club rather than guessing.
