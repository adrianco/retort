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

## Implementation

A C# / .NET 10 MCP server implementing the spec, built test-first (TDD: a failing test
was written before each piece of implementation code).

### Layout

- `src/BrazilianSoccerMcp.Core` - data loading, normalization, and query logic (no I/O
  framework dependencies beyond CsvHelper for parsing).
- `src/BrazilianSoccerMcp.Server` - console host that exposes the Core query services as
  MCP tools over stdio, using the official `ModelContextProtocol` C# SDK.
- `tests/BrazilianSoccerMcp.Core.Tests` - xUnit test suite (94 tests) covering every
  Core component, including full-file loads of all 6 CSV datasets.

### Core components

- **Normalization** (`TeamNameNormalizer`, `FlexibleDateParser`, `CompetitionParser`,
  `TextNormalizer`): reconciles the data-quality issues called out in the spec - team
  names with/without state suffixes, accented vs. unaccented spelling, multiple date
  formats, and free-text competition names. Two base names ("Atlético", "América") are
  shared by several genuinely distinct clubs (e.g. Atlético-MG, Atlético-GO,
  Atlético-PR are different real teams) - the normalizer keeps their state suffix
  instead of merging them, and resolves BR-Football-Dataset's descriptive spellings
  (e.g. "Atletico Mineiro") to the same canonical key.
- **Loaders** (`Data/*Loader.cs`): one loader per CSV file/schema, producing a unified
  `MatchRecord` or `PlayerRecord` model.
- **`MatchDeduplicator`**: several files cover overlapping competitions/seasons and
  report the same real-world fixture (e.g. a 2019 Brasileirão match appears in both
  `Brasileirao_Matches.csv` and `BR-Football-Dataset.csv`); this collapses duplicates,
  preferring the more authoritative dedicated source per competition.
  Deduplication reduces the raw 23,954 match rows to ~19,700 distinct fixtures.
- **`SoccerDataStore`**: in-memory repository indexing matches by normalized team key
  for fast, name-variant-tolerant lookups.
- **Query services** (`Queries/*QueryService.cs`): `MatchQueryService` (match search,
  head-to-head), `TeamQueryService` (win/loss/draw records), `PlayerQueryService`
  (search/filter/top-rated), `CompetitionQueryService` (standings, champions -
  calculated from match results), `StatisticsQueryService` (goal averages, biggest
  wins, best home/away records).
- **`ResponseFormatter`**: renders query results as the plain-text answer format shown
  in the spec's examples.

### MCP tools

`SoccerTools` (in the Server project) exposes 13 MCP tools wrapping the query
services: `find_matches`, `get_head_to_head`, `get_team_record`,
`search_players_by_name`, `find_players_by_nationality`, `find_players_by_club`,
`get_top_rated_players`, `get_standings`, `get_champion`,
`get_average_goals_per_match`, `get_biggest_wins`, `get_best_home_record`,
`get_best_away_record`.

### Running

```bash
dotnet build BrazilianSoccerMcp.slnx
dotnet test BrazilianSoccerMcp.slnx
dotnet run --project src/BrazilianSoccerMcp.Server   # starts the MCP server over stdio
```

The server locates `data/kaggle` automatically by walking up from the working
directory; override with `--data-dir <path>` or the `BRAZILIAN_SOCCER_DATA_DIR`
environment variable.
