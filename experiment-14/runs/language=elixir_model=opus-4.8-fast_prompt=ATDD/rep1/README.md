# Brazilian Soccer MCP Server (Elixir)

An [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server that answers
natural-language questions about Brazilian football — players, teams, matches and
competitions — over the provided Kaggle datasets. It speaks JSON-RPC 2.0 (the MCP wire
protocol) over stdio, so it can be plugged into any MCP host/LLM.

Built per [`TASK.md`](TASK.md) / [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
using executable **Acceptance Test-Driven Development**: every requirement in the spec was
first written as an automated acceptance test that drives the SUT only through the public
MCP protocol, and the implementation was built until the whole suite passed.

## Quick start

```bash
mix deps.get          # fetch jason + nimble_csv
mix test              # run the acceptance + unit suite
mix run -e 'BrazilianSoccer.MCP.Stdio.run()'   # start the MCP server on stdio
```

Talk to it with newline-delimited JSON-RPC, e.g.:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"competition_standings","arguments":{"competition":"Brasileirão","season":2019}}}' \
  | mix run -e 'BrazilianSoccer.MCP.Stdio.run()'
```

Registering it with an MCP host (Claude Desktop-style config):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "mix",
      "args": ["run", "-e", "BrazilianSoccer.MCP.Stdio.run()"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

## MCP tools

The server advertises eight tools (via `tools/list`), covering all five capability
categories in the spec. Every `tools/call` returns a human-readable `content` text block
and a machine-readable `structuredContent` payload.

| Tool | Category | Purpose |
|------|----------|---------|
| `find_matches` | Match Queries | Find matches by team, opponent, competition, season or date range |
| `head_to_head` | Match / Statistical | Win/draw/loss record and match list between two clubs |
| `team_record` | Team Queries | A club's W/D/L, goals for/against and win rate (by venue/season/competition) |
| `search_players` | Player Queries | Search FIFA players by name, nationality, club, position, min rating |
| `get_player` | Player Queries | Look up a single player by name |
| `competition_standings` | Competition Queries | League table for a season, calculated from match results |
| `competition_statistics` | Statistical Analysis | Goals/match, home/away/draw rates, biggest wins |
| `list_competitions` | Competition Queries | Known competitions, or those a given club has appeared in |

### Example questions it answers

- "Show me all Flamengo vs Fluminense matches" → `find_matches` (team + opponent)
- "What matches did Palmeiras play in 2023?" → `find_matches` (team + season)
- "What is Corinthians' home record in 2019?" → `team_record` (venue=home)
- "Compare Palmeiras and Santos head-to-head" → `head_to_head`
- "Who is Neymar?" → `get_player`
- "Find the top Brazilian players" → `search_players` (nationality=Brazil)
- "Who won the 2019 Brasileirão?" → `competition_standings` (Flamengo, 90 pts)
- "What's the average goals per match in the Brasileirão?" → `competition_statistics`
- "What competitions has Palmeiras played in?" → `list_competitions` (team)

## Architecture

```
MCP host / LLM
   │  JSON-RPC 2.0 (stdio)
   ▼
BrazilianSoccer.MCP.Stdio          ← newline-delimited transport
   │
BrazilianSoccer.MCP.Server         ← initialize / tools/list / tools/call dispatch (public boundary)
   │
BrazilianSoccer.MCP.Tools          ← tool catalogue + argument handling (+ Format for text)
   │
Matches · Teams · Players · Competitions · Statistics   ← domain queries
   │
BrazilianSoccer.Store              ← in-memory dataset (:persistent_term, read-only)
   │
BrazilianSoccer.Loader + Normalize ← CSV parsing, team-name/date normalisation, de-dup
```

### Data handling

The six CSV files are loaded once at start-up into memory (≈20k de-duplicated matches and
≈18k players; load is well under a second). The spec's data-quality challenges are handled in
`BrazilianSoccer.Normalize` and `BrazilianSoccer.Loader`:

- **Team name variations** — a canonical key strips state/country suffixes
  (`Palmeiras-SP` → `Palmeiras`, `Nacional (URU)` → `Nacional`) and folds accents/case, so
  `Palmeiras`, `Palmeiras-SP` and `São Paulo`/`Sao Paulo` all match consistently.
- **Date formats** — ISO (`2023-09-24`), ISO+time (`2012-05-19 18:30:00`) and Brazilian
  `DD/MM/YYYY` are all parsed; `NA`/blank become `nil`.
- **UTF-8 / BOM** — accents are preserved for display and a UTF-8 BOM in the FIFA file is stripped.
- **Cross-source duplication** — the same fixture appears in several files. The general match
  set is de-duplicated; season aggregates (standings, statistics) deliberately use a single
  authoritative source per competition-season so results are never double-counted. This
  reproduces the known 2019 Brasileirão table (Flamengo champion, 90 pts, 380 matches).

### Configuration

By default the loader reads `data/kaggle/` next to the source. Point it elsewhere with:

```elixir
config :brazilian_soccer, data_dir: "/some/other/dir"
```

## Tests

The acceptance suite (`test/acceptance/`) is the executable specification. Each test acts as
an external MCP client (`test/support/mcp_client.ex`) — it encodes JSON-RPC requests, sends
them through the server's public `handle_json/1` entry point, and asserts on the domain
result. There is no back-door access to internal modules. Tests are organised by spec
category: protocol, match, team, player, competition and statistics queries.

```bash
mix test
```

## Data sources

Kaggle data can't be downloaded without an account, so these freely-available datasets were
pre-downloaded into `data/kaggle/`:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — CC BY 4.0
  - `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — CC0 Public Domain
  - `BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — CC BY 4.0
  - `novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — Apache 2.0
  - `fifa_data.csv`
