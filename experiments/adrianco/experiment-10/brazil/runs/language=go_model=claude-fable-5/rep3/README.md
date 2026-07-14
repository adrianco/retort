# Brazilian Soccer MCP Server

A dependency-free Go implementation of an MCP (Model Context Protocol) server
that answers natural-language questions about Brazilian soccer from six Kaggle
datasets (16,800+ deduplicated matches across Brasileirão Séries A/B/C, Copa do
Brasil and Copa Libertadores, plus 18,207 FIFA player records).

## Specification
brazilian-soccer-mcp-guide.md (also TASK.md)

## Implementation

Plain Go (no third-party modules). The server loads all CSVs into memory at
startup (~0.5s) and serves the MCP protocol (JSON-RPC 2.0, newline-delimited)
over stdio.

```
main.go                     entry point: load data, serve MCP on stdio
internal/data/models.go     Match / Player / Dataset model
internal/data/normalize.go  team-name normalization (accents, state suffixes,
                            "EC/FC" tokens, aliases like Athletico-PR)
internal/data/loader.go     per-file CSV loaders, multi-format date parsing,
                            cross-dataset fixture deduplication (±1 day fuzz)
internal/query/engine.go    match search, head-to-head, team records,
                            calculated standings, player search, aggregates
internal/query/format.go    plain-text answer formatting
internal/mcp/protocol.go    minimal MCP/JSON-RPC stdio server
internal/mcp/tools.go       the nine MCP tool definitions
```

Key data-quality handling (per the spec):
- **Team name variations** — "Palmeiras-SP", "Palmeiras", "São Paulo"/"Sao
  Paulo", "Athletico-PR"/"Atletico-PR", "Vasco da Gama RJ"/"Vasco",
  "Fortaleza EC" etc. all normalize to one canonical key; ambiguous bases
  (Atlético-MG/PR/GO, América-MG/RN, Botafogo-RJ/SP/PB) keep their state.
- **Date formats** — ISO ("2023-09-24"), ISO datetime ("2012-05-19 18:30:00")
  and Brazilian ("29/03/2003") all parse.
- **Deduplication** — the same fixture appears in up to three source files
  (sometimes dated one day apart); ~7,000 duplicates are merged so standings
  and statistics are not double counted. The calculated 2019 Série A table
  reproduces the real one exactly (Flamengo champion, 90 pts, 28W 6D 4L).
- **UTF-8** — accented names are preserved for display and folded for matching.

## MCP Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | matches by team, opponent, competition, season, date range |
| `head_to_head` | win/draw/goal comparison plus match list for two teams |
| `team_stats` | W/D/L, goals, win rate; filter by season/competition/venue |
| `league_standings` | league table calculated from results for a season |
| `search_players` | FIFA players by name/nationality/club/position/rating |
| `player_details` | full attribute card for one player |
| `competition_stats` | matches, avg goals, home/away win rates |
| `biggest_wins` | largest margins of victory |
| `list_teams` | resolve team-name spellings known to the dataset |

## Build, test, run

```sh
go build -o brazilian-soccer-mcp .   # build the server
go test ./...                        # run the BDD test suite
./brazilian-soccer-mcp               # serves MCP on stdio (auto-finds data/kaggle)
./brazilian-soccer-mcp -data /path/to/data/kaggle -quiet
```

Claude Desktop / Claude Code configuration:

```json
{"mcpServers": {"brazilian-soccer": {"command": "/path/to/brazilian-soccer-mcp"}}}
```

## Testing

BDD (Given/When/Then) scenarios in `internal/*/..._test.go` run against the
real datasets and cover the spec's success criteria: all six CSVs load, team
name variants resolve, the documented example queries work (Fla-Flu
head-to-head, Corinthians' 2022 home record, 2019 champion), 20 sample
questions are answered through the MCP tool interface, and simple lookups
finish in <2s / aggregates in <5s.

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
