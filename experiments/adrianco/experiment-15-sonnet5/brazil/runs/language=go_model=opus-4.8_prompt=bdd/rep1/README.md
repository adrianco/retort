# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server, written in Go,
that answers natural-language questions about Brazilian soccer — matches, teams, players,
competitions and statistics — from the bundled Kaggle datasets. Connect it to any
MCP-capable LLM client (e.g. Claude Desktop) and ask questions like *"Who won the 2019
Brasileirão?"* or *"Compare Flamengo and Fluminense head-to-head."*

It implements the specification in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## Quick start

```bash
# Build
go build -o brazilian-soccer-mcp .

# Run (speaks JSON-RPC 2.0 over stdio; diagnostics go to stderr)
./brazilian-soccer-mcp -data data/kaggle
```

Register it with an MCP client, for example Claude Desktop
(`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brazilian-soccer-mcp",
      "args": ["-data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

You can also drive it by hand — one JSON-RPC message per line:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019}}}' \
  | ./brazilian-soccer-mcp -data data/kaggle
```

## Tools

The server advertises seven tools via `tools/list`:

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `search_players` | "Find all Brazilian players", "Who are the highest-rated players at Grêmio?" |
| `match_statistics` | "What's the average goals per match?", "Show me the biggest wins" |
| `data_overview` | "What data is loaded?" |

Every tool returns a human-readable text answer. Filters accept team-name variations
(with or without a state suffix, accented or not) and multiple date formats.

## Design notes

The interesting engineering is in reconciling six heterogeneous CSV files into one clean,
queryable corpus.

- **Layout / format tolerance** (`internal/soccer/loader.go`). Each file has its own
  columns, date format (`2019-04-27`, `27/04/2019`, `2012-05-19 18:30:00`) and goal
  encoding (`2`, `2.0`, blank/`NA`). Columns are looked up by name — a missing column
  yields an empty value rather than silently reading the wrong one — and unparseable rows
  are skipped rather than failing the whole load.

- **Team-name normalisation** (`internal/soccer/normalize.go`). The same club is spelled
  many ways across datasets, and a bare base name can be ambiguous: `Atletico-MG`
  (Mineiro), `Atletico-PR` (Paranaense) and `Atletico-GO` (Goianiense) are three
  different clubs. A canonical-alias layer maps every known variant
  (`Athletico`, `Atletico Paranaense`, `EC Bahia`, `Vasco Da Gama RJ`, …) to a single key,
  while unambiguous clubs fall back to accent-folded, suffix-stripped keys. This is why
  `sao paulo` matches `São Paulo-SP` but the three Atléticos stay separate.

- **Cross-dataset de-duplication** (`internal/soccer/store.go`). Several files overlap —
  the 2019 Brasileirão appears in three of them — which would otherwise triple every
  team's games and points. Fixtures are collapsed by match day (± one day, since sources
  disagree by a day due to kick-off vs UTC dates) and teams, keeping the cleaner
  league-file record and merging in any extended statistics from the duplicate. The
  computed 2019 Brasileirão table matches reality: Flamengo champions on 90 points from
  38 games.

- **MCP transport** (`internal/mcp/`). A minimal, dependency-free JSON-RPC 2.0
  implementation over the stdio transport (`initialize`, `tools/list`, `tools/call`).

### Package layout

```
main.go                     entrypoint: load data, serve over stdio
internal/soccer/            domain model, CSV loading, normalisation, query engine
internal/mcp/               MCP server (JSON-RPC 2.0 over stdio) + tool definitions
data/kaggle/                bundled datasets (see Data Sources below)
```

## Testing

```bash
go test ./...
```

Tests are written in a BDD style (`Given/When/Then`, behaviour-named). They cover
normalisation, per-file parsing, the query engine and the MCP protocol against small
in-memory fixtures, plus integration tests that load the real datasets and assert
spec-level facts (e.g. Flamengo win the 2019 Brasileirão with 90 points). The integration
tests skip automatically if `data/kaggle` is absent.

## Data Sources

Kaggle data can't be downloaded without an account, so these freely-available datasets
(used with attribution) are included under `data/kaggle/`:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/Brasileirao_Matches.csv`
- `data/kaggle/Brazilian_Cup_Matches.csv`
- `data/kaggle/Libertadores_Matches.csv`

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- `data/kaggle/BR-Football-Dataset.csv`

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/novo_campeonato_brasileiro.csv`

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- `data/kaggle/fifa_data.csv`

### Data caveats

- The FIFA player database is from the FIFA 19 era and, due to licensing, omits some
  Brazilian league clubs (e.g. Flamengo) and players (e.g. Gabriel Barbosa). Queries for
  those return "no players found" — a data limitation, not a bug.
- 2023 Brasileirão data comes only from the BR-Football file, which has no round numbers,
  so those matches display without a round.

## Specification

See [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).
