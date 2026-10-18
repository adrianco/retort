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

## Implementation (C#)

An MCP server written in C# (.NET 10), with no external MCP dependency. It speaks
newline-delimited JSON-RPC over stdio.

- `src/BrazilianSoccerMcp/` - the server
  - `Csv.cs` - RFC 4180 reader (quotes, BOM, embedded newlines)
  - `TeamNames.cs` - team-name normalization (state suffixes, accents, FC/EC affixes, aliases)
  - `DataLoader.cs` - loads the six CSVs; de-duplicates fixtures that appear in more than one file
  - `SoccerQueries.cs` - match, team, head-to-head, standings, statistics and player queries
  - `SoccerTools.cs` - MCP tools and their text answers
  - `McpServer.cs` - MCP protocol handling (initialize, ping, tools/list, tools/call)
- `tests/BrazilianSoccerMcp.Tests/` - xUnit behaviour tests (Given/When/Then names) run against the real data

Run the tests:

```
dotnet test tests/BrazilianSoccerMcp.Tests
```

Run the server (finds `data/kaggle` automatically, or pass `--data <dir>`):

```
dotnet run --project src/BrazilianSoccerMcp
```

Tools: `search_matches`, `team_record`, `head_to_head`, `standings`, `match_statistics`,
`search_players`, `brazilian_club_summary`.

Example MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "dotnet",
      "args": ["run", "--project", "/absolute/path/to/src/BrazilianSoccerMcp"]
    }
  }
}
```

### Known data limitations

- The FIFA file is a FIFA 19 snapshot. It contains no Flamengo squad, so player queries for
  Flamengo return nothing.
- Brasileirão 2012–2019 appears in two files and in BR-Football's "Serie A". Fixtures are
  de-duplicated by competition, year, teams and score, so each league match is counted once.
