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

## Implementation (C# / .NET)

An MCP (Model Context Protocol) server over stdio, implemented in C# with no
external runtime dependencies (the JSON-RPC 2.0 / MCP layer is hand-rolled on
`System.Text.Json`).

```
src/BrazilianSoccer.Core/     Library: CSV parsing, team-name normalization,
                              unified data model, query engine, MCP protocol
  Csv.cs                      RFC-4180-style CSV parser (quotes, UTF-8 BOM)
  TeamNames.cs                Canonical team keys ("Palmeiras-SP" == "Palmeiras",
                              "São Paulo" == "Sao Paulo", "EC Bahia" == "Bahia")
  DataStore.cs                Loads all 6 CSVs; dedups overlapping datasets on
                              (date ±1 day, home, away) and merges extra detail
  QueryService.cs             Match/team/player/competition/statistics queries
  McpServer.cs                JSON-RPC 2.0 over newline-delimited stdio
  SoccerTools.cs              The 9 MCP tool definitions + JSON schemas
src/BrazilianSoccer.Server/   Console executable (stdio transport)
tests/BrazilianSoccer.Tests/  xUnit BDD-style scenarios (110 tests)
```

### Build, test, run

```bash
dotnet build
dotnet test
dotnet run --project src/BrazilianSoccer.Server            # finds data/kaggle automatically
dotnet run --project src/BrazilianSoccer.Server -- /path/to/data/kaggle
```

All protocol traffic is on stdout; diagnostics go to stderr. Register with an
MCP client (e.g. Claude Desktop / Claude Code) as a stdio server:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "dotnet",
      "args": ["run", "--project", "<repo>/src/BrazilianSoccer.Server"]
    }
  }
}
```

### Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team, opponent, competition, season, date range |
| `head_to_head` | Full match list + win/draw/goal totals for two teams |
| `get_team_stats` | W/D/L, goals, win rate; filter by season/competition/venue |
| `get_standings` | Season league table calculated from results, names the champion |
| `search_players` | FIFA players by name, nationality, club, position, min rating |
| `get_player` | Detailed FIFA profile for one player |
| `get_competition_stats` | Avg goals, home/draw/away rates, top scoring teams |
| `get_biggest_wins` | Largest margins of victory |
| `list_competitions` | Data coverage overview (competitions, seasons, files) |

### Data handling notes

- The three Brasileirão sources overlap (2012-2019 twice, plus BR-Football
  2014-2023); matches are deduplicated on (date, home, away) with a ±1 day
  window because kick-off dates differ by one day between sources for evening
  matches. Unique matches: ~18.8k from ~24k raw rows.
- Team names are normalized across "Palmeiras-SP" / "Palmeiras" /
  "Sport Club Corinthians Paulista" style variants, with explicit handling of
  ambiguous bases (Atlético-MG vs Athletico-PR vs Atlético-GO, Botafogo-RJ vs
  Botafogo-SP/PB, América-MG vs América-RN, Santos vs Santos-AP).
- The FIFA 19 player file does not include Flamengo, Corinthians, Palmeiras or
  São Paulo squads (unlicensed in that edition); player-by-club queries work
  for the licensed Brazilian clubs (Grêmio, Santos, Cruzeiro, Internacional,
  Atlético Mineiro, Fluminense, Botafogo, Bahia, etc.).
- Requires ICU (do not enable `InvariantGlobalization`): accent folding uses
  Unicode NFD normalization; the server verifies this at startup.
