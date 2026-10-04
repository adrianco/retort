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

## C# MCP server

`src/BrazilianSoccerMcp` is a .NET 10 MCP server (JSON-RPC over stdio, no external packages) that loads the six CSV files into memory and exposes 16 tools: `search_matches`, `head_to_head`, `team_stats`, `team_profile`, `standings`, `competition_bracket`, `competition_stats`, `compare_seasons`, `team_rankings`, `biggest_wins`, `find_derbies`, `search_players`, `player_profile`, `club_player_summary`, `list_teams`, `dataset_info`.

```bash
dotnet test                                   # BDD-style xUnit scenarios against the real data
dotnet run --project src/BrazilianSoccerMcp   # start the server on stdio
```

MCP client configuration:

```json
{ "mcpServers": { "brazilian-soccer": { "command": "dotnet", "args": ["run", "--project", "src/BrazilianSoccerMcp"] } } }
```

The data directory is found by walking up from the working directory to `data/kaggle`; override it with the `BRAZILIAN_SOCCER_DATA` environment variable or a path argument.

Notes on the data:
- Team spellings are normalised (`Palmeiras-SP`, `Palmeiras - SP`, `Palmeiras`), while clubs that share a name stay distinct by state (`Atlético-MG` / `Atlético-GO`, `Botafogo` / `Botafogo-SP`).
- The same fixture appears in up to three files; duplicates are merged, so 23,854 scored match rows become 16,756 unique matches.
- Standings are calculated from results. Seasons that are incomplete in the source files (e.g. Série A 2015 and 2023) are flagged and not given a champion.
- There is no goal-scorer data, and the FIFA file has no squads for Flamengo, Palmeiras, Corinthians or São Paulo.
