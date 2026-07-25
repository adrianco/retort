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

## MCP Server Implementation (C)

`bsmcp` is an MCP (Model Context Protocol) server written in portable C11
with no external dependencies. It loads all six CSV datasets into memory and
serves JSON-RPC 2.0 over stdio (one message per line), implementing
`initialize`, `ping`, `tools/list` and `tools/call`.

### Build and test

    make            # builds ./bsmcp (server) and ./test_bsmcp (tests)
    make test       # runs the BDD unit suite + the MCP protocol e2e test

### Run

    ./bsmcp [data-dir]        # default data dir: data/kaggle

Register with an MCP client (e.g. Claude Desktop / Claude Code) as a stdio
server with command `/path/to/bsmcp` and argument `/path/to/data/kaggle`.

### Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team, opponent, competition, season, round/stage, date range; head-to-head summary when two teams given |
| `get_team_stats` | W/D/L, goals, win rate; home/away split; per-competition breakdown |
| `head_to_head` | Full head-to-head record and recent meetings |
| `search_players` | FIFA 19 players by name, nationality, club, position, min rating |
| `get_standings` | Season table computed from results (champion/relegation marked) |
| `get_league_stats` | Goals per match, home-win rate, biggest wins |
| `list_competitions` | Dataset coverage summary |

### Implementation notes

- **Team-name normalization**: accents folded, case/punctuation ignored,
  state suffixes handled ("Flamengo" matches "Flamengo-RJ"). Matching is
  suffix-aware so Atlético-MG never matches Athletico-PR, and an alias table
  reconciles spellings across datasets ("Atletico Mineiro" = "Atlético-MG").
- **Deduplication**: Série A 2012–2019 appears in three files; each
  (competition, season) is served from one canonical source so records and
  standings are never double counted.
- **Gap filling**: rows with "NA" scores (late 2022 Brasileirão fixtures)
  are repaired from other datasets covering the same fixture, tolerating the
  one-day UTC date shift in BR-Football-Dataset.csv.
- **Dates**: ISO (`2023-09-24`, with or without time) and Brazilian
  (`29/03/2003`) formats are parsed; all data is handled as UTF-8.

Source files: `bsmcp.h` (declarations), `csv.c` (CSV reader), `json.c`
(JSON parser/writer), `data.c` (loading + normalization), `tools.c` (query
tools), `mcp_main.c` (JSON-RPC stdio loop), `test_main.c` + `test_mcp.sh`
(tests).
