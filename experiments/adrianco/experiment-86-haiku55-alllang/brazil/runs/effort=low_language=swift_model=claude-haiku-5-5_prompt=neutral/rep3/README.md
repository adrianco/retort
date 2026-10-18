# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## What was built
A Swift MCP server (stdio, JSON-RPC 2.0, no third-party dependencies) that answers questions about Brazilian soccer matches, teams, standings and players from the CSVs in `data/kaggle/`.

- `Sources/SoccerCore/` – CSV parsing, team-name normalization, the six dataset loaders, the query engine, the rule-based natural-language router and the MCP tool layer.
- `Sources/soccer-mcp/` – the executable.
- `Tests/SoccerCoreTests/` – 57 XCTest cases in Given/When/Then form covering the spec's requirements, including the example questions.

### Build, test, run
```
swift build -c release
swift test
.build/release/soccer-mcp [data-directory]   # default: $SOCCER_DATA_DIR or ./data/kaggle
```
Startup loads about 16.7k matches and 18.2k players in roughly half a second.

Example MCP client entry:
```json
{ "mcpServers": { "brazilian-soccer": { "command": "/path/to/.build/release/soccer-mcp", "args": ["/path/to/data/kaggle"] } } }
```

### Tools
| Tool | Purpose |
|------|---------|
| `ask` | Natural-language question; routed to one of the tools below and the interpretation is shown |
| `search_matches` | Matches by team, opponent, competition, season, date range and venue |
| `team_record` | Wins/draws/losses, goals and win rate |
| `head_to_head` | Meetings between two teams |
| `standings` | Season table calculated from results (3/1/0 points) |
| `rank_teams` | Teams ranked by win rate, wins, goals or points |
| `league_stats` | Average goals and home/draw/away rates |
| `biggest_wins` | Largest margins |
| `search_players` | FIFA data by name, nationality, club, position and overall rating |

### Data handling
- **Season precedence**: the files overlap by whole seasons (Serie A 2012–2019 is in two files). Each (competition, season) is taken from the first source that covers it, in the order Brasileirao_Matches, novo_campeonato, Brazilian_Cup, Libertadores, BR-Football. Matching individual games across files is unreliable because team spellings differ and some dates are a day apart.
- **Team names**: state suffixes (`Palmeiras-SP`), parentheticals and accents are normalized; a team's state is kept when the source gives it, so `Atlético-MG` and `Atlético-PR` stay separate.
- **Coverage limits**: the FIFA file has no Flamengo players, so club-level player queries for some clubs return nothing. The Kaggle match data runs to 2023 and the FIFA ratings are from an older edition.

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
