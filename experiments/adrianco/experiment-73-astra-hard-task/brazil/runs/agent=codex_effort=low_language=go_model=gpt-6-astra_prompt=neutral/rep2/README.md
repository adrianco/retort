# Brazilian Soccer MCP (Go)

A dependency-free, read-only stdio MCP server over all six bundled Kaggle CSVs. An attached LLM translates natural-language questions to tools and formats answers. No API keys, external services, or network access are needed at runtime.

## Run

```sh
go build -o soccer-mcp .
./soccer-mcp -data ./data/kaggle
```

Configure an MCP client with absolute paths (the client's working directory may differ):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/soccer-mcp",
      "args": ["-data", "/absolute/path/data/kaggle"]
    }
  }
}
```

The server reads newline-delimited JSON-RPC on stdin and writes only protocol responses to stdout. Diagnostics go to stderr. Supports initialization, notifications, ping, tool discovery and tool calls; negotiates MCP 2024-11-05, 2025-03-26 or 2025-06-18. Transport follows the [MCP stdio specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).

## Tools and graph

Canonical team identifiers link matches, competitions/seasons, and historical FIFA players. Match edges carry scores, round/stage and all original CSV rows; player nodes retain all FIFA attributes. `team_info` traverses these relationships in one query. Everything is loaded once into memory.

| Tool | Purpose |
|---|---|
| `search_matches` | Match history, schedules, derbies, cup stage results and biggest wins |
| `search_players` | Partial name, nationality, club and position search, highest overall first |
| `team_info` | Record, home/away splits, season trends, competition performance and linked players |
| `head_to_head` | Both directions of a pairing, record from the requested team's perspective |
| `standings` | Calculated Brasileirão table for a season |
| `statistics` | Goals, averages, home win percentage, season comparison and team rankings |
| `data_info` | Source counts, score conflicts and limitations |

Match filters: `team`, `opponent`, `venue` (`home`, `away`, `either`), `competition`, `season`, inclusive ISO `from`/`to`, exact `round`/`stage`, `source` filename, `derbies`. `sort: "biggest_win"` orders matches by score margin. By default matches are newest first. `limit` defaults to 50, maximum 1000; `offset` pages through results. Totals cover the entire filtered set. Aggregations use every matching completed fixture regardless of pagination.

Player filters: `name`, `nationality` (use `Brazil`), `club`, `position` (FIFA code or `forwards`). Rankings include original attributes. Statistics rank teams by win percentage (with sample size), or goals scored with `sort: "goals"`; `venue` selects home/away rankings.

Example tool call after initialization:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team":"Flamengo-RJ","opponent":"Fluminense"}}}
```

Results contain readable JSON text and structured content. The LLM client owns conversational context, including follow-ups such as “What was the score?”; the server does not guess a prior match.

## Sample questions

| Question | Tool and arguments |
|---|---|
| Show Flamengo vs Fluminense matches | `search_matches`: team Flamengo, opponent Fluminense |
| What did Palmeiras play in 2023? | `search_matches`: team Palmeiras, season 2023 |
| Find Copa do Brasil finals | `search_matches`: competition Copa do Brasil; inspect source round codes (see caveats) |
| Corinthians home record in 2022? | `team_info`: team Corinthians, venue home, season 2022 |
| Most goals in Serie A 2023? | `statistics`: competition Serie A, season 2023, sort goals |
| Compare Palmeiras and Santos | `head_to_head`: team Palmeiras, opponent Santos |
| All Brazilian FIFA players | `search_players`: nationality Brazil; paginate |
| Highest-rated players at Flamengo | `search_players`: club Flamengo |
| Forwards at São Paulo FC | `search_players`: club São Paulo FC, position forwards |
| Who won the 2019 Brasileirão? | `standings`: competition Brasileirão, season 2019; report calculated leader |
| Show 2018 Libertadores bracket | `search_matches`: competition Libertadores, season 2018; group by recorded stage |
| Who was relegated in 2020? | `standings`: competition Brasileirão, season 2020; explain coverage and official-status limitation |
| Average Brasileirão goals | `statistics`: competition Brasileirão |
| Best away record | `statistics`: venue away |
| Biggest wins | `search_matches`: sort biggest_win |
| Last Flamengo–Corinthians match | `search_matches`: team Flamengo, opponent Corinthians, limit 1 |
| Who is Gabriel Barbosa? | `search_players`: name Gabriel Barbosa; report no match if absent |
| Show derbies in 2023 | `search_matches`: derbies true, season 2023 |
| Palmeiras competition participation | `team_info`: team Palmeiras |
| Best home record | `statistics`: venue home |
| Compare 2018 and 2019 | `statistics`: from 2018-01-01, to 2019-12-31; inspect by_season |
| Who scored the most individual goals? | Explain that scorer events are absent; team goals are available |

## Data policy and limits

- Team matching is case/accent insensitive, removes Brazilian state suffixes, and maps known full-name aliases. Qualifiers are preserved for ambiguous clubs such as América-MG/RN and Atlético-MG/GO/PR. The curated derby list is not exhaustive; unknown aliases may require the source spelling.
- ISO dates, Brazilian dates and timestamp formats are accepted. Unknown source dates remain empty and seasons may be zero; scores missing in the source are null and excluded from calculations. Malformed dates, CSV rows and missing required files fail startup with context.
- Matches with the same competition/date/home/away merge. Brasileirão's double round robin additionally merges by season/ordered pairing, accounting for source date discrepancies. Every source row remains attached. Other competitions can retain duplicates where dates/names differ.
- Source precedence: Brasileirão matches, Brazilian Cup, Libertadores, extended statistics, historical Brasileirão. First score wins conflicts (visible through `data_info`); a later complete score fills a missing result.
- Standings award 3/1/0 points and sort by points, wins, goal difference, goals scored, then canonical name. They do not incorporate deductions or every official tie-break. Historical seasons can be incomplete. The 2019 regression verifies 380 fixtures and Flamengo's 90 points.
- Cup CSV rounds are numeric and their meaning varies by season. No unsupported automatic final-round mapping is applied. Libertadores has stage labels. These records permit stage-grouped results, but not an authoritative bracket where progression/penalties are missing.
- Relegation, official championship declarations and individual top scorers cannot always be inferred. The LLM should explain that limitation rather than invent facts. FIFA data is a historical snapshot; it does not establish current clubs or match participation.

## Verification

```sh
go test -v ./...
go test -race ./...
go vet ./...
go build ./...
```

Tests cover normalization, date/score handling, filters, exact statistics, H2H, player attributes, pagination, invalid inputs, MCP framing/errors, source provenance, real dataset loading, 21 example query routes and query latency below two seconds.

## Dataset attribution (demo/non-commercial use)

- Brasileirão, Copa do Brasil, Libertadores: [Ricardo Mattos / Kaggle](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro), CC BY 4.0.
- Extended match statistics: [cuecacuela / Kaggle](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches), CC0.
- Historical Brasileirão: [macedojleo / Kaggle](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019), CC BY 4.0.
- FIFA players: [youssefelbadry10 / Kaggle](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data), Apache 2.0.

Transformations normalize names/dates and combine duplicate records; original values are retained in responses.
