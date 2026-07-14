# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in
Go, that exposes a queryable knowledge base of Brazilian soccer — matches,
teams, players and competitions — built from the bundled Kaggle datasets. An
LLM (or any MCP client) connects over stdio and calls the server's tools to
answer natural-language questions like *"Who won the 2019 Brasileirão?"* or
*"Compare Palmeiras and Santos head-to-head."*

Specification: [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
(also mirrored in `TASK.md`).

## What was built

A self-contained, dependency-free Go MCP server (standard library only):

| File | Responsibility |
|------|----------------|
| `main.go` | Entry point: loads data, registers tools, runs the stdio loop |
| `mcp.go` | Minimal MCP / JSON-RPC 2.0 implementation (initialize, tools/list, tools/call) |
| `model.go` | Core `Match` and `Player` domain types |
| `normalize.go` | Team-name, accent, date and number normalization |
| `loader.go` | Reads the six CSV datasets into normalized records |
| `store.go` | In-memory query engine (matches, records, standings, stats, players) |
| `tools.go` | The seven MCP tools and their text formatting |

Every source file opens with a context block comment describing its role.

### MCP tools

| Tool | Capability area | Example question |
|------|-----------------|------------------|
| `find_matches` | Match queries | "Show me all Flamengo vs Fluminense matches" |
| `team_stats` | Team queries | "What is Corinthians' home record in 2022?" |
| `head_to_head` | Statistical analysis | "Compare Palmeiras and Santos head-to-head" |
| `search_players` | Player queries | "Who are the top Brazilian players?" |
| `standings` | Competition queries | "Who won the 2019 Brasileirão?" |
| `competition_stats` | Statistical analysis | "What's the average goals per match?" |
| `list_competitions` | Discovery | "What competitions and seasons are available?" |

### Data-quality handling

The datasets disagree on spelling, formats and encoding; the server normalizes
all of it (see `normalize.go`):

- **Team names** — state suffixes (`Palmeiras-SP`), country codes
  (`Nacional (URU)`) and bare names are folded to a canonical key. Crucially,
  the key *keeps* a state suffix so distinct same-named clubs (Atlético-**MG**
  vs Atlético-**PR**) never merge, while a bare query like `"Flamengo"` still
  matches `Flamengo-RJ` across every dataset.
- **Dates** — ISO (`2023-09-24`), Brazilian (`29/03/2003`) and timestamped
  (`2012-05-19 18:30:00`) forms all parse.
- **Encoding** — Portuguese accents (`São`, `Grêmio`, `Avaí`) are folded for
  matching but preserved for display.
- **Overlapping sources** — the Brasileirão appears in three datasets.
  Cross-dataset duplicates are collapsed by signature for match/head-to-head
  queries, and **standings are computed from a single authoritative source per
  competition/season** so games are never double-counted. The computed 2019
  Brasileirão table reproduces the real result (Flamengo champion, 90 pts, 38
  games) — verified by an integration test.

## Building and running

```bash
go build -o brazilian-soccer-mcp .
./brazilian-soccer-mcp            # speaks MCP over stdin/stdout
```

The data directory defaults to `data/kaggle`; override with `--data <dir>` or
the `BR_SOCCER_DATA` environment variable. Progress/diagnostics go to stderr so
they never corrupt the JSON-RPC stream on stdout.

### Connecting an MCP client

Example client configuration (e.g. Claude Desktop `mcpServers` entry):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brazilian-soccer-mcp",
      "args": ["--data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

### Quick manual smoke test

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"limit":5}}}' \
  | ./brazilian-soccer-mcp
```

## Testing

BDD-style Given/When/Then tests cover the normalization layer, the query engine
(against a deterministic fixture), the MCP protocol/tool handlers, and the real
bundled datasets (integration tests that assert known historical results).

```bash
go test ./...
```

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets have been downloaded for use here:

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
