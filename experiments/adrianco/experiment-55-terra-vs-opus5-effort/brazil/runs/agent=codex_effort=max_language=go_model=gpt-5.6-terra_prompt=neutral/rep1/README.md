# Brazilian Soccer MCP Server

A self-contained Go MCP (Model Context Protocol) server for querying the six Brazilian soccer CSV datasets in `data/kaggle/`. It runs over standard input/output, loads all data into memory at startup, and needs no database or external services.

## Run

From the repository root:

```sh
go run .
```

The process speaks newline-delimited JSON-RPC on stdout, as required for MCP stdio servers. Diagnostics are written only to stderr.

For a quick local check without an MCP client:

```sh
go run . --query "Who won the 2019 Brasileirão?"
go run . --query "When did Flamengo last play Corinthians?"
```

Use `--data-dir /path/to/csvs` or `BRAZILIAN_SOCCER_DATA_DIR` to point at another copy of the six CSV files.

An MCP client can launch it with a configuration equivalent to:

```json
{
  "command": "go",
  "args": ["run", "."],
  "cwd": "/absolute/path/to/this/repository"
}
```

## Tools

`query_brazilian_soccer` is the natural-language entry point. It recognizes common English and Portuguese question patterns including latest matches, team records, head-to-head comparisons, player searches, standings, relegation candidates, derbies, finals, biggest wins, and season comparisons.

Focused tools are also available when an MCP client knows what it needs:

- `search_matches` — filters by team, opponent, home/away team, date range, competition, season, round, stage, source, derby, or final.
- `team_statistics` and `head_to_head` — calculate records, goals, points, and win rates.
- `search_players` — filters FIFA players by name, nationality, club, position, and rating.
- `competition_standings` and `competition_statistics` — calculate tables, average goals, biggest wins, most goals, and best home/away records.
- `team_competitions`, `compare_seasons`, `competition_bracket` (Libertadores knockout rounds), and `list_data_sources`.

The server also exposes MCP resources with a dataset inventory and a sample prompt.

## Data behavior

All six supplied files are loaded and can be queried explicitly using the `source` argument:

- `Brasileirao_Matches.csv`
- `Brazilian_Cup_Matches.csv`
- `Libertadores_Matches.csv`
- `BR-Football-Dataset.csv` (`source: "extended"`)
- `novo_campeonato_brasileiro.csv` (`source: "historical"`)
- `fifa_data.csv`

Team lookup is accent-insensitive and handles common variants such as `Palmeiras-SP`/`Palmeiras`, `São Paulo FC`/`Sao Paulo`, and formal club names such as `Sport Club Corinthians Paulista`.

Several match sources overlap. By default, queries choose the source with the most scored rows for each competition and season, then collapse duplicate physical matches. This gives reliable calculated standings while retaining raw-source access through `source` or `include_duplicates: true`.

Dates accept ISO dates, datetimes, and Brazilian `DD/MM/YYYY` dates. Responses use ISO dates and include the source file.

## Dataset provenance

- Brasileirão, Copa do Brasil, and Libertadores matches: [Kaggle — jogos do campeonato brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro), CC BY 4.0.
- Extended match statistics: [Kaggle — brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches), CC0.
- Historical Brasileirão 2003–2019: [Kaggle — campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019), CC BY 4.0.
- FIFA players: [Kaggle — fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data), Apache 2.0.

## Development

```sh
go test ./...
go vet ./...
go build -o /tmp/brazilian-soccer-mcp .
```

The test suite uses BDD-style Given/When/Then scenarios against the real datasets. It verifies all files load, normalized match queries, the 2019 Brasileirão table, player search, final-stage filtering, aggregate statistics, natural-language routing, and MCP JSON-RPC behavior.
