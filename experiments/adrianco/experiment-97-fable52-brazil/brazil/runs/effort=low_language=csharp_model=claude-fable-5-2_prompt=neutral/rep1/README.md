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

## Implementation (C# / .NET 10)

An MCP server (JSON-RPC 2.0 over stdio, no third-party runtime dependencies) that loads the six CSV files
into memory and exposes 15 tools.

```bash
dotnet build
dotnet test                                   # 142 BDD-style xUnit scenarios against the real data
dotnet run --project src/BrazilianSoccerMcp   # run as an MCP server on stdio
# one-off query without an MCP client:
dotnet run --project src/BrazilianSoccerMcp -- --call standings '{"season":2019}'
```

MCP client configuration:

```json
{ "mcpServers": { "brazilian-soccer": {
    "command": "dotnet",
    "args": ["run", "--project", "<repo>/src/BrazilianSoccerMcp"] } } }
```

The data directory is found by walking up from the working directory to `data/kaggle`; override with
`--data <dir>` or `BRAZILIAN_SOCCER_DATA_DIR`.

Tools: `search_matches`, `head_to_head`, `team_stats`, `team_profile`, `standings`, `knockout_bracket`,
`competition_stats`, `compare_seasons`, `rank_teams`, `biggest_wins`, `derbies`, `search_players`,
`player_profile`, `players_by_club`, `dataset_info`.

Layout:
- `src/BrazilianSoccerMcp/Csv.cs` – CSV reader (quotes, BOM, UTF-8)
- `TeamNames.cs` – team-name normalisation ("Palmeiras-SP", "América - MG", "Atletico Mineiro" ...)
- `DataStore.cs` – loading, date parsing, merging of fixtures that appear in several files
- `SoccerQueries.cs` – query layer (matches, records, standings, rankings, players)
- `SoccerTools.cs` – MCP tool definitions and answer formatting
- `McpServer.cs`, `Program.cs` – protocol and entry point
- `tests/BrazilianSoccerMcp.Tests` – scenarios per feature

Data notes:
- The three Série A sources overlap; the same fixture is stored once (16,727 unique played matches) so
  statistics are not double counted. Unplayed fixtures (score `NA`/`-`) are skipped.
- Standings are computed from results only (no points deductions or official tie-breakers). A champion and
  relegation zone are reported only when every team has played a full double round-robin.
- The FIFA file has no Flamengo, Palmeiras, Corinthians or São Paulo squads; player queries for those clubs say so.
