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

## Run the C# MCP server

From this directory, using the .NET 10 SDK:

```sh
dotnet build -c Release
dotnet test -c Release --no-build
```

The tests send MCP requests through the server's stdio handler and check answers against the bundled datasets. They also cover protocol negotiation, errors, pagination and response times. You can also run them with `dotnet run -c Release --no-build -- --test`. The project needs no NuGet packages or API credentials.

Configure a stdio-capable MCP host using its server settings. For hosts that accept the following configuration format, replace the example path with the absolute path to the built DLL.

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "dotnet",
      "args": ["/absolute/path/to/bin/Release/net10.0/BrazilianSoccer.dll"]
    }
  }
}
```

The build copies the CSVs alongside the DLL. You can supply an alternate data directory as the second entry in `args`. The host's language model translates natural-language questions into tool calls through the [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).

| Question | Tool and example filters |
| --- | --- |
| When did Flamengo last play Corinthians? | `search_matches` with `team: Flamengo`, `opponent: Corinthians`, `limit: 1` |
| What was Corinthians' 2022 home record? | `team_stats` with `team: Corinthians`, `season: 2022`, `competition: Serie A`, `venue: home` |
| Who won the 2019 Brasileirão? | `standings` with `season: 2019` |
| Show the 2018 Libertadores bracket. | `competition_results` with `competition: Libertadores`, `season: 2018`, `knockoutOnly: true` |
| Show Grêmio's players and its 2019 results summary. | `club_profile` with `club: Gremio`, `season: 2019`, `competition: Serie A` |
| Compare average goals across the 2018 and 2019 league seasons. | `match_statistics` with `competition: Serie A`, `from: 2018-01-01`, `to: 2019-12-31` |

Tool results include JSON text and structured content. Use `nextOffset` to fetch subsequent pages. `dataset_info` reports source counts and seasons. To inspect original fixture fields, pass a CSV filename as `source`.

## Data interpretation

The server links teams, fixtures, competition editions and FIFA clubs through normalized names. Default match queries reconcile overlapping datasets and include the contributing source filenames. Kickoff dates and times follow the selected source's conventions. Extended match statistics remain available where the feed supplies them. Missing scores are excluded from win, draw, loss and goal calculations.

The Série A table uses the available results and flags incomplete editions, including 2023 with 377 scored matches. Table positions are calculated from scores and may differ from official standings where administrative adjustments or further tie-breakers apply. The FIFA 19 club and player data is a historical snapshot with limited Brazilian club coverage. Individual goal scorers are unavailable in the supplied match files.
