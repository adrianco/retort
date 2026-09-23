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

## Implementation (Objective-C / Foundation)

An MCP server (JSON-RPC 2.0 over stdio) that answers questions about Brazilian soccer from the six CSV files.

```
make            # builds build/brazilian-soccer-mcp and build/tests
make test       # runs the BDD (Given/When/Then) suite
./build/brazilian-soccer-mcp                                  # MCP stdio server
./build/brazilian-soccer-mcp standings '{"season":2019}'      # run one tool from the CLI
```

The data directory defaults to `data/kaggle` (override with `BS_DATA_DIR`).
MCP client config: `{"command": "/path/to/build/brazilian-soccer-mcp", "env": {"BS_DATA_DIR": "/path/to/data/kaggle"}}`.

| File | Purpose |
|------|---------|
| `src/BSCSV.*` | RFC 4180 CSV parser (quotes, BOM, UTF-8) |
| `src/BSTeamNames.*` | Team name normalization ("Palmeiras-SP", "Vasco Da Gama RJ", "Atlético - MG", "Sport Club Corinthians Paulista") |
| `src/BSModels.*` | Match and player objects |
| `src/BSDatabase.*` | Loads all files, de-duplicates overlapping matches across files, runs queries |
| `src/BSTools.*` | MCP tool schemas and formatted answers |
| `src/BSMCPServer.*` | JSON-RPC: `initialize`, `ping`, `tools/list`, `tools/call` |
| `tests/BSTests.m` | 32 BDD scenarios covering every query category, the protocol, and timing |

Tools: `search_matches`, `head_to_head`, `team_stats`, `standings`, `search_players`, `competition_stats`,
`biggest_wins`, `rank_teams`, `cup_finals`, `knockout_bracket`, `derbies`, `team_competitions`,
`compare_seasons`, `brazilian_clubs_players`, `dataset_info`.

Data notes: the FIFA file is FIFA 19 and has no Flamengo, Palmeiras or Gabriel Barbosa entries, so those player
queries correctly return no results. The 2023 Série A data is missing a few matches, so the computed 2023 table is incomplete.
Relegation is shown as the bottom four of a 20-team table.
