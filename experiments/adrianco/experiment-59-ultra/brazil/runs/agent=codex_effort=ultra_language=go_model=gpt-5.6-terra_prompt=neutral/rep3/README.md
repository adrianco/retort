# Brazilian Soccer MCP Server

A self-contained Go MCP (Model Context Protocol) server for the six Brazilian
soccer CSV datasets included in this repository. It runs over MCP's standard
newline-delimited JSON-RPC stdio transport and does not require a database,
network access, or optional third-party APIs.

## Run

Build the server:

```sh
go build -o brazilian-soccer-mcp .
```

Run it from this repository (the default data location is `data/kaggle`):

```sh
./brazilian-soccer-mcp
```

When the binary is launched elsewhere, give it an absolute data path:

```sh
./brazilian-soccer-mcp --data-dir /absolute/path/to/data/kaggle
```

`BRAZILIAN_SOCCER_DATA_DIR` is an equivalent environment-variable override.
The server writes MCP messages only to stdout; startup and error diagnostics go
to stderr.

Example MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brazilian-soccer-mcp",
      "args": ["--data-dir", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

## Tools

| Tool | Purpose |
| --- | --- |
| `dataset_summary` | List the six loaded datasets and their record counts. |
| `search_matches` | Find fixtures by team, opponent, date, competition, season, round, stage, or source. |
| `team_statistics` | Calculate a team's all/home/away W-D-L record and goals. |
| `team_profile` | Follow a team across match results and the FIFA club snapshot. |
| `head_to_head` | Compare two teams and return their fixtures and record. |
| `search_players` | Search FIFA players by name, nationality, club, position, or rating. |
| `competition_standings` | Calculate season standings from match results. |
| `competition_statistics` | Calculate goals-per-match, home/away rates, and biggest wins. |
| `team_rankings` | Rank teams by goals scored, home record, or away record. |
| `soccer_query` | Handle a small set of common natural-language questions deterministically. |

The structured tools are the preferred LLM integration surface. All list tools
return JSON text plus MCP `structuredContent`, so an MCP client can consume the
results reliably.

## Data behavior

- All six supplied CSVs are loaded at startup: four current/historical match
  sources, extended match statistics, and FIFA players.
- Team comparison is case-, accent-, punctuation-, and state-suffix-aware.
  State suffixes remain in returned names so similarly named teams are not
  silently merged.
- ISO datetime, ISO date, and Brazilian `DD/MM/YYYY` formats are accepted.
- `NA` and `-` scores are retained as incomplete fixtures for search, but are
  excluded from calculated records, standings, and aggregates.
- Several match sources overlap. By default, calculated results select a
  canonical source for each competition-season (`Brasileirao_Matches.csv`, then
  historical and extended data; analogous rules for the cups) to avoid double
  counting. Pass `source` or `include_all_sources: true` to control this.
- The supplied files do not contain goal-scorer data. The server reports top
  scorers as unsupported rather than inventing results.
- Standings use points, wins, goal difference, goals scored, then alphabetical
  order as a transparent calculated tie-break sequence.

## Data sources and licenses

- `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, and
  `Libertadores_Matches.csv`: [Kaggle — jogos do campeonato brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro), CC BY 4.0.
- `BR-Football-Dataset.csv`: [Kaggle — brazilian football matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches), CC0.
- `novo_campeonato_brasileiro.csv`: [Kaggle — campeonato brasileiro 2003–2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019), CC BY 4.0.
- `fifa_data.csv`: [Kaggle — FIFA players data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data), Apache 2.0.

## Verify

```sh
go test -count=1 ./...
go vet ./...
go test -race ./...
go build ./...
```

The test suite includes Given/When/Then-style behavior tests for all six file
schemas, BOM handling, date and score variations, overlap policy, standings,
team normalization, and an MCP stdio handshake/tool-call smoke test.
