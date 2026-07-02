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

A C# (.NET 10) MCP server implementing the spec in `TASK.md`/`brazilian-soccer-mcp-guide.md`.

```
src/BrazilianSoccerMcp.Data/     Data loading, normalization and query logic (no MCP dependency, fully unit-testable)
  Csv/                          Hand-rolled RFC4180 CSV parser (quoted fields, embedded commas/quotes, UTF-8/BOM)
  Models/                       MatchRecord, PlayerRecord, Competition
  Normalization/                TeamNameNormalizer - unifies state-suffix/accent/punctuation variants across files
  Loading/                      Per-file loaders for the 5 match CSVs + fifa_data.csv
  Queries/                      MatchQueryService, StatsQueryService, PlayerQueryService
  Formatting/                   Renders query results as the plain-text answers a client can relay to a user
src/BrazilianSoccerMcp.Server/   MCP server (stdio transport) exposing the query services as tools
tests/BrazilianSoccerMcp.Tests/  xUnit tests: normalizer, CSV parsing, data loading, query services, 24 sample
                                 questions covering all 5 required capability categories, and response-time checks
```

### Team name normalization

The datasets spell the same club differently ("Palmeiras-SP", "Palmeiras", "Sociedade Esportiva
Palmeiras", accented/unaccented). `TeamNameNormalizer` reduces a raw name to a match key that keeps
the state/country suffix (e.g. "atletico-mg") rather than discarding it, because several base names
are shared by distinct clubs from different states (Atlético-MG, Atlético-GO and Athletico-PR are
three different clubs). A query for an unqualified name like "Flamengo" matches any state variant;
a qualified query like "Atletico-MG" matches only that club. A small alias table maps well-known long
official names (e.g. "Sport Club Internacional") to their canonical key. This is a best-effort,
rule-based normalizer, not full entity resolution.

### Known data limitations

- `fifa_data.csv` is a FIFA 19 export; Flamengo, Palmeiras, Corinthians and São Paulo were unlicensed
  in that game and are entirely absent from the `Club` column, so player-by-club queries for those
  clubs correctly return no results.
- `Brasileirao_Matches.csv` covers 2012-2022; more recent seasons are only in `BR-Football-Dataset.csv`.
- Standings/statistics are computed from a single dataset per call to avoid double-counting matches
  that appear in more than one of the provided CSV files.

### Running

```
dotnet build BrazilianSoccerMcp.slnx
dotnet test BrazilianSoccerMcp.slnx
dotnet run --project src/BrazilianSoccerMcp.Server
```

The server locates `data/kaggle` automatically by walking up from the executable/working directory;
override with the `BRAZIL_SOCCER_DATA_DIR` environment variable or a `--data-dir=<path>` argument if
running from elsewhere.

### Tools exposed

`search_matches`, `head_to_head`, `team_record`, `compare_teams`, `list_teams`, `standings`,
`biggest_wins`, `average_goals`, `best_records`, `search_players`, `players_by_nationality`,
`players_by_club`, `top_players`.
