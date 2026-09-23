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

## Go MCP server

Build and run (stdio JSON-RPC MCP transport, no external dependencies):

    go build -o brazilian-soccer-mcp .
    ./brazilian-soccer-mcp -data data/kaggle

Claude Code: `claude mcp add brazilian-soccer -- /path/to/brazilian-soccer-mcp -data /path/to/data/kaggle`

Tools: search_matches, head_to_head, team_stats, standings, competition_stats, team_rankings,
compare_seasons, team_competitions, derbies, search_players, player_details,
brazilian_clubs_players, team_profile, dataset_info.

Tests: `go test ./...`
