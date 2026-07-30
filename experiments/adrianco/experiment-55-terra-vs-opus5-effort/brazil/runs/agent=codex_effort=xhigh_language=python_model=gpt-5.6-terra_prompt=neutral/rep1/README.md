# Brazilian Soccer MCP

An MCP (Model Context Protocol) server for querying the Brazilian soccer CSVs bundled in this repository. It loads all five match datasets and the FIFA player dataset into an in-memory, read-only query service. Team matching is accent-insensitive and reconciles common variants such as `Flamengo-RJ`, `São Paulo FC`, and `Sport Club Corinthians Paulista`.

## Run

Use Python 3.10 or newer. Install the declared MCP dependency, then start the standard-input/output server:

```bash
python3 -m pip install .
brazilian-soccer-mcp
```

For a local client configuration, use:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "brazilian-soccer-mcp"
    }
  }
}
```

The server exposes these tools:

- `data_summary` — records loaded from each source.
- `search_matches` — filter by teams, competition, season, dates, stage, round, or source.
- `team_statistics` and `head_to_head` — win/draw/loss and goal calculations.
- `team_overview` — cross-file club profile with match data and FIFA player records.
- `competition_standings` and `competition_statistics` — points tables, rates, scoring leaders, and biggest wins.
- `search_players` — filters by name, nationality, club, position, and rating.
- `answer_question` — routes common English or Portuguese question forms to one of the structured queries.

Match searches deduplicate identical source records by default. Statistical tools additionally choose the dedicated competition dataset in preference to overlapping rows in the extended-statistics file, preventing the same fixture from being counted multiple times. Pass `include_duplicates=true` to inspect every underlying record, or use the `source` parameter to query a particular CSV.

## Test

```bash
python3 -m pytest
```

The test suite checks all six CSVs are loaded, normalized team searches, date and competition filtering, calculated records and standings, cross-file club/player data, player filters, natural-language routing, and invalid query validation.

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
