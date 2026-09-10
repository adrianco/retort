# Brazilian Soccer MCP server

A dependency-free Go server using all six bundled CSVs. All source code lives in the repository root. Data is loaded once into an in-memory graph of normalized teams, matches, competition seasons, and historical FIFA players. No API keys, downloads, database service, or network access are needed at runtime.

## Build and run

```sh
go build -o soccer-mcp .
./soccer-mcp -data /absolute/path/to/data/kaggle
```

The process serves newline-delimited JSON-RPC over stdin/stdout. It exits on EOF. Errors go to stderr. The default data directory is `data/kaggle` relative to the process working directory; use an absolute path in MCP clients.

Example client configuration (replace both paths):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/soccer-mcp",
      "args": ["-data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

The MCP client supplies the LLM that translates natural-language questions into tool calls and writes conversational answers. The server supplies deterministic data and calculations; it does not embed a model or an English keyword parser. Follow-ups such as “What was the score?” use the client conversation's previous match result.

## Protocol

Implements MCP revision `2024-11-05`: initialization/version negotiation, initialized notification, ping, tools/list, tools/call, JSON-RPC errors, and notification suppression. Unknown requested protocol versions receive the supported version; the client decides whether to proceed. Send initialization and then the initialized notification before tool calls. Requests must be single JSON objects, one per line (maximum 4 MiB). Responses contain MCP text content with readable JSON. Query validation errors set `isError`; malformed calls use JSON-RPC errors. All tools are read-only.

References: [MCP stdio transport](https://modelcontextprotocol.io/specification/2024-11-05/basic/transports), [MCP tools](https://modelcontextprotocol.io/specification/2024-11-05/server/tools).

Example input:

```jsonl
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"example","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team":"Flamengo","opponent":"Fluminense","season":2023,"limit":10}}}
```

## Tools and filters

| Tool | Result |
|---|---|
| `search_matches` | Matches with scores, dates, competition, round/stage, sources, and original CSV attributes |
| `search_players` | Rating-ranked players with all original FIFA attributes |
| `team_stats` | W/D/L, goals, points, win percentage, home/away splits, competition and season trends, match history |
| `head_to_head` | Both teams' records and fixtures in either home/away direction |
| `team_profile` | Team statistics and historical player roster across files |
| `standings` | Calculated Serie A or B season table |
| `statistics` | Goal averages, home/away wins, season comparisons, team rankings and biggest margins |
| `competition_info` | Competition fixtures grouped by competition, season, round and stage |
| `graph` | Nodes and typed relationships for a team's matches, opponents, competition seasons and players |
| `data_info` | Per-file row counts, unique entities, available team names, conflict warnings and limitations |

Match filters: `team`, `opponent` (requires team), `venue` (`home`, `away`, `either`), `competition`, `season`, `from`, `to`, `stage`, `source` (CSV basename), and `derby`. Dates are inclusive; unknown dates are excluded from bounded date searches. Matches sort newest first; `sort: "biggest_win"` sorts by absolute goal difference. Unplayed results sort last in biggest wins.

Player filters: `name` substring, `nationality`, `club` normalized substring, and `position` (FIFA code or `forwards`). Results sort by Overall descending, then name. `Brazilian` is accepted for `Brazil`.

Pagination: `limit` defaults to 50 and has maximum 500; `offset` defaults to 0. List results contain `total`, `items`, and `next_offset` (null at the end). Aggregates always use the entire filtered set, independently of pagination. Graph offsets page matches and players independently; their totals are returned. `standings` returns the full table. `statistics` accepts `sort: "goals"` or `"win_rate"`; `venue` selects home/away team records. Win-rate rankings have no minimum-games threshold; inspect played counts.

Team tools and graph require `team`; head-to-head also requires `opponent`. Standings require `competition` and `season`. Use competition/date/season filters for comparable standings; team or venue filters produce a restricted table.

## Example questions and tool calls

These mappings are exercised by the sample-question tests. Empty results are valid evidence of missing coverage, especially FIFA club/name lookups.

| Question | Tool | Arguments |
|---|---|---|
| Show Flamengo vs Fluminense matches | search_matches | `{"team":"Flamengo","opponent":"Fluminense"}` |
| What did Palmeiras play in 2023? | search_matches | `{"team":"Palmeiras","season":2023}` |
| Find Copa do Brasil finals | search_matches | `{"competition":"Copa do Brasil","stage":"final"}` |
| Corinthians' home record in 2022? | team_stats | `{"team":"Corinthians","venue":"home","season":2022}` |
| Who scored most team goals in Serie A 2023? | statistics | `{"competition":"Serie A","season":2023,"sort":"goals"}` |
| Compare Palmeiras and Santos | head_to_head | `{"team":"Palmeiras","opponent":"Santos"}` |
| Find Brazilian players | search_players | `{"nationality":"Brazil"}` |
| Highest rated Flamengo players? | search_players | `{"club":"Flamengo"}` |
| São Paulo forwards? | search_players | `{"club":"São Paulo FC","position":"forwards"}` |
| Who tops the calculated 2019 league table? | standings | `{"competition":"Serie A","season":2019}` |
| Show 2018 Libertadores knockout fixtures | competition_info | `{"competition":"Libertadores","season":2018}` |
| Who finished at the bottom in 2020? | standings | `{"competition":"Serie A","season":2020}` |
| Average Serie A goals? | statistics | `{"competition":"Serie A"}` |
| Best away record? | statistics | `{"venue":"away","sort":"win_rate"}` |
| Biggest wins? | search_matches | `{"sort":"biggest_win"}` |
| Last Flamengo–Corinthians score? | search_matches | `{"team":"Flamengo","opponent":"Corinthians","limit":1}` |
| Who is Gabriel Barbosa? | search_players | `{"name":"Gabriel"}` (inspect candidates; do not assume identity) |
| Flamengo squad and match history? | team_profile | `{"team":"Flamengo"}` |
| Derbies in 2023? | search_matches | `{"season":2023,"derby":true}` |
| Palmeiras' competitions? | team_stats | `{"team":"Palmeiras"}` |
| Compare 2018 and 2019 | statistics | `{"from":"2018-01-01","to":"2019-12-31"}` |
| Explore Flamengo's relationships | graph | `{"team":"Flamengo"}` |

## Data quality and scope

- UTF-8 names are retained in source attributes. Matching folds case and Portuguese accents, strips state suffixes and resolves known aliases. State distinctions are preserved for ambiguous Atlético, América, Botafogo and Bragantino clubs. This is a curated alias set, not universal entity resolution; use `data_info` to inspect names. No fuzzy player identity claims are made.
- Serie A/B fixture identity is competition + season + normalized home/away team, exploiting their double round-robin format. This reconciles source date discrepancies. Other competitions use competition + date + home/away team; some cross-date cup duplicates may remain. Score conflicts retain the first source and emit warnings. Data loading order is the order of files in `data.go`; primary competition files precede extended/historical enrichment. Original missing attributes are filled from later sources. Source membership and raw row counts remain queryable.
- Missing scores remain null, excluded from records and goal averages. Missing dates remain empty with a warning. Invalid CSV headers, malformed records, invalid non-missing dates, and invalid scores fail startup with file/row context.
- Numeric Copa do Brasil rounds vary across seasons. The maximum observed round per season is marked `final (inferred from maximum recorded round)`. It may be incorrect if coverage is incomplete. Textual Libertadores `final` is matched exactly, excluding semifinals and quarterfinals.
- Standings use 3 points per win, 1 per draw; ties sort by wins, goal difference, goals for, then name. They cannot account for sanctions or all official tie-breakers. Incomplete season coverage is possible. Champion and relegation claims require interpretation and coverage checks; the server does not mark official champions or relegated teams.
- Cup fixtures are available by round/stage, but penalty results, aggregate tie decisions and advancement edges are not reliably provided. No invented bracket winners. Individual goalscorers cannot be inferred from team scores. FIFA Finishing is a rating, not a goal tally.
- Player clubs/ratings are a historical FIFA snapshot, not current squads or match-season membership. Graph player edges explicitly say `plays_for_snapshot`. A missing player or club is returned as an empty result.
- Derbies use the curated list in `query.go`; it is not an exhaustive rivalry database. All answers concern the supplied data, not live schedules.

## Tests

```sh
go test ./...
go test -race ./...
go vet ./...
go test -run '^$' -bench . -benchmem
```

Tests cover all six actual datasets, at least 20 question mappings, known 2019 standings (20 clubs; Flamengo 90 points in 38 games), normalization, dates, missing/malformed scores, deduplication/enrichment, head-to-head, filtering, player attributes and ranking, graph links, aggregation, pagination, and MCP lifecycle/error behavior. Benchmarks measure queries after loading. Tests use local files only.

## Attribution

Demo/non-commercial use as requested. Original CSV files are unchanged.

- Brasileirão, Copa do Brasil and Libertadores: [Ricardo Mattos, Kaggle](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro), CC BY 4.0.
- Extended match statistics: [cuecacuela, Kaggle](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches), CC0.
- Historical Brasileirão: [macedojleo, Kaggle](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019), CC BY 4.0 as supplied.
- FIFA players: [youssefelbadry10, Kaggle](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data), Apache 2.0 as supplied.

Normalization, merging, derived records and graph relationships are transformations performed by this implementation. Data source licenses do not imply endorsement.
