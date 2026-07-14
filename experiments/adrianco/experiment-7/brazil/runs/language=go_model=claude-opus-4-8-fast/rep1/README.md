# Brazilian Soccer MCP Server (Go)

An [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server that
answers natural-language questions about Brazilian soccer — matches, teams,
players, competitions, and statistics — over the bundled Kaggle datasets.

It is implemented in Go with **no external dependencies** (standard library
only) and speaks the MCP **stdio JSON-RPC 2.0** transport, so any MCP-capable
client (e.g. an LLM host) can connect to it and call its tools.

The specification this implements is [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
(identical to `TASK.md`).

## Quick start

```bash
# Build
go build -o brazilian-soccer-mcp .

# Run (reads MCP requests on stdin, writes responses on stdout;
# logs go to stderr so they never corrupt the JSON-RPC stream)
./brazilian-soccer-mcp            # uses ./data/kaggle by default
./brazilian-soccer-mcp -data /path/to/data/kaggle
SOCCER_DATA_DIR=/path/to/data ./brazilian-soccer-mcp
```

Smoke-test it from the shell (newline-delimited JSON-RPC):

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"limit":5}}}' \
  | ./brazilian-soccer-mcp
```

### Configuring an MCP client

Point your MCP client at the built binary. Example client config:

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

## Tools

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `find_matches` | Find matches by team, opponent (head-to-head), competition, season, or date range | `team`, `opponent`, `competition`, `season`, `date_from`, `date_to`, `limit` |
| `head_to_head` | Win/draw/loss + goals between two teams, plus recent meetings | `team_a`, `team_b`, `limit` |
| `team_stats` | A team's record (W/D/L, goals, win rate), filterable by competition/season/venue | `team`, `competition`, `season`, `venue` |
| `standings` | League table computed from match results | `competition`, `season`, `limit` |
| `search_players` | Search FIFA players by name/nationality/club/position/min rating | `name`, `nationality`, `club`, `position`, `min_overall`, `limit` |
| `competition_stats` | Aggregate stats (avg goals/match, home/away/draw split) | `competition`, `season` |
| `biggest_wins` | Largest goal margins | `competition`, `season`, `limit` |
| `list_competitions` | Competitions and season ranges available | – |

These cover all five capability areas required by the spec: match queries, team
queries, player queries, competition queries, and statistical analysis.

### Example

`standings` for the 2019 Brasileirão reproduces the historical table:

```
Brasileirão Série A 2019 standings (calculated from matches):
 1. Flamengo-RJ                   90 pts (28W  6D  4L, GF 86 GA 37, +49)
 2. Santos-SP                     74 pts (22W  8D  8L, GF 60 GA 33, +27)
 3. Palmeiras-SP                  74 pts (21W 11D  6L, GF 61 GA 32, +29)
 ...
```

## Architecture

```
main.go                     # CLI entry point: load data, register tools, serve stdio
internal/mcp/               # Dependency-free MCP/JSON-RPC 2.0 stdio server
internal/store/             # Data model, CSV loading, normalization, queries
internal/server/            # Tool definitions: schema + arg decoding + text formatting
data/kaggle/                # Bundled datasets (see Data sources below)
```

Each source file begins with a context-block comment describing its role.

### Data handling

The six CSV files are normalized into two in-memory collections (`Matches`,
`Players`). The datasets are small enough (~17k matches, ~18k players after
processing) to keep entirely in memory; all queries respond well under the
spec's latency targets (full load + several queries complete in < 1 s).

The spec's stated data-quality challenges are handled explicitly:

- **Team-name variations** — `NormalizeTeam` folds accents (São → sao, Grêmio →
  gremio) and strips state/country suffixes (`Palmeiras-SP`, `América - MG`,
  `Nacional (URU)`). User queries match any spelling via accent-folded substring
  matching.
- **State disambiguation & cross-file dedup** — the same fixtures appear in
  multiple files (the Brasileirão is in both `Brasileirao_Matches.csv` and
  `novo_campeonato_brasileiro.csv`, and again as "Serie A" in
  `BR-Football-Dataset.csv`). Naïvely merging them inflated standings ~3×. A
  **state-aware team key** keeps genuinely different clubs apart (Atlético-**MG**
  vs Athletico-**PR**) while merging spelling variants of the same club
  (Vasco / Vasco da Gama, Athletico / Atlético-PR). Fixtures are then
  de-duplicated by competition + teams + season + date. `BR-Football-Dataset.csv`
  rows for competitions owned by a dedicated, state-annotated file (Série A, Copa
  do Brasil, Libertadores) are dropped as duplicates; it still contributes its
  **unique** Série B and Série C matches.
- **Date formats** — ISO datetimes, ISO dates, and Brazilian `DD/MM/YYYY` are all
  parsed.
- **Encoding** — files are read as UTF-8; the BOM on `fifa_data.csv` is stripped.

### Notes on data coverage

The FIFA player database is FIFA-19-era and does **not** include every Brazilian
club or player (e.g. Flamengo is absent; "Gabriel Barbosa" is not listed). Such
queries correctly return "No players found" rather than erroring. Many Brazilian
clubs and players (Santos, Grêmio, Internacional, Gabriel Jesus, Neymar, …) are
present.

## Testing

Tests follow a BDD **Given/When/Then** structure (as requested by the spec's
"Testing Approach"). Each `TestScenario_*` function maps to a Gherkin-style
scenario, with `// Given` / `// When` / `// Then` comments marking the phases.

```bash
go test ./...
```

Coverage includes:

- **Data loading** — all six datasets load; competitions present; dedup yields a
  realistic 2019 Série A season size (~380 fixtures, champion Flamengo on 90 pts)
  rather than the un-deduplicated ~3× inflation.
- **Normalization** — accent/suffix stripping, state disambiguation, fuzzy team
  matching.
- **Queries** — find matches, head-to-head, team stats, standings ordering,
  competition stats, biggest wins, player search/filtering.
- **MCP protocol** — `initialize`, `tools/list`, `tools/call`, notifications
  (no response), unknown method/tool errors, and handler errors surfaced as
  `isError` tool results.
- **End-to-end** — every tool driven through the real `tools/call` path against
  the real datasets.

## Implementation summary

- Language: **Go** (standard library only).
- Transport: MCP over stdio, JSON-RPC 2.0, protocol version `2024-11-05`.
- 8 tools spanning all required query categories.
- Robust CSV ingestion, team-name normalization, and cross-dataset
  deduplication for accurate standings and statistics.
- BDD (Given/When/Then) test suite across the data, query, protocol, and
  end-to-end layers.

---

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
