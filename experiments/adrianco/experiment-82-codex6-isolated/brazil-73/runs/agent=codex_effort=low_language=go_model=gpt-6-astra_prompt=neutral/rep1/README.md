# Brazilian Soccer MCP Server

A dependency-free Go MCP server for the six supplied Kaggle CSV files. It loads an in-memory knowledge graph linking normalized teams to matches, competition-seasons and historical FIFA players. An MCP host's LLM interprets natural-language questions and invokes the tools; this server does not require an API key or implement a separate language model.

## Run

Requires Go 1.22 or later. Run from this directory:

```sh
go build -o soccer-mcp .
./soccer-mcp -data ./data/kaggle
```

The process reads newline-delimited JSON-RPC from stdin and writes only MCP responses to stdout. Startup errors go to stderr and exit nonzero. All six files must exist; malformed records fail with filename and row context. No network access or optional data APIs are used.

Configure an MCP host with absolute paths (substitute your actual directory):

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

Supports `initialize`, `notifications/initialized`, `ping`, `tools/list`, and `tools/call` over stdio. Negotiates protocol versions 2024-11-05, 2025-03-26 and 2025-06-18; unknown requested versions receive 2025-06-18. Uses the [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) and [tool response format](https://modelcontextprotocol.io/specification/2025-06-18/server/tools). Notifications do not receive responses. Invalid requests produce JSON-RPC errors; tool execution/argument errors return `isError: true`.

A minimal session, one JSON object per line:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"demo","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team":"Flamengo","opponent":"Fluminense","season":2023}}}
```

## Tools

| Tool | Purpose |
|---|---|
| `dataset_info` | Source row counts, licenses, warnings, known rivalries and limitations |
| `search_matches` | Match history, schedules, scores, raw corners/shots/attacks and source provenance |
| `search_players` | Name, nationality, club, position, ratings and all FIFA attributes |
| `team_profile` | Team record, home/away split, competitions, matches and linked FIFA roster |
| `head_to_head` | Both teams' records and fixtures in either orientation |
| `standings` | Calculated league table for a required competition and season |
| `competition_results` | Results and stage counts; stage/round filters expose knockout legs |
| `statistics` | Goals, win rates, team rankings and season-by-season performance |

Match filters: `team`, `opponent` (requires team), `venue` (`home`, `away`, `either`), `competition`, `season`, `from`, `to` (inclusive ISO dates), `stage`, `round`, exact CSV `source`, and `derbies`. Matches are newest first; `sort: "biggest_win"` sorts by absolute goal margin. A team filter uses the team's graph adjacency index.

Player filters: `name` (substring), `nationality`, `club` (normalized exact match, then substring fallback), `position` (exact FIFA code or `forwards`). Players sort by descending overall rating. Club and player associations are historical.

`limit` defaults to 50, maximum 500; `offset` defaults to zero. Lists return `total`, `items`, and `next_offset` when another page exists. Aggregation always uses the complete filtered result, not just the displayed page. `statistics` accepts `sort: "goals"`, `"win_rate"`, or `"points"` for its team list. Check `played` when comparing win rates. `team_profile` match filters do not constrain the historical FIFA roster.

## Example questions

An LLM can translate these questions into the following tool arguments. Empty results mean the supplied dataset has no matching records, not that the player or fixture does not exist.

| Question | Tool | Arguments |
|---|---|---|
| Show Flamengo vs Fluminense | `head_to_head` | `{"team":"Flamengo","opponent":"Fluminense"}` |
| What matches did Palmeiras play in 2023? | `search_matches` | `{"team":"Palmeiras","season":2023}` |
| Find Copa do Brasil finals | `search_matches` | `{"competition":"Copa do Brasil","stage":"final"}` |
| Corinthians home record in 2022? | `team_profile` | `{"team":"Corinthians","venue":"home","season":2022}` |
| Most goals in Serie A 2023? | `statistics` | `{"competition":"Serie A","season":2023,"sort":"goals"}` |
| Compare Palmeiras and Santos | `head_to_head` | `{"team":"Palmeiras","opponent":"Santos"}` |
| Find Brazilian players | `search_players` | `{"nationality":"Brazil"}` |
| Highest-rated Flamengo players? | `search_players` | `{"club":"Flamengo"}` |
| São Paulo forwards? | `search_players` | `{"club":"São Paulo FC","position":"forwards"}` |
| Who leads the calculated 2019 league table? | `standings` | `{"competition":"Serie A","season":2019}` |
| Show 2018 Libertadores knockout results | `competition_results` | `{"competition":"Libertadores","season":2018}` |
| Bottom league positions in 2020? | `standings` | `{"competition":"Serie A","season":2020}` |
| Average goals in Brasileirão? | `statistics` | `{"competition":"Brasileirão"}` |
| Best away record? | `statistics` | `{"venue":"away","sort":"win_rate"}` |
| Biggest victories? | `search_matches` | `{"sort":"biggest_win","limit":10}` |
| When did Flamengo last play Corinthians? | `search_matches` | `{"team":"Flamengo","opponent":"Corinthians","limit":1}` |
| Who is Gabriel Barbosa? | `search_players` | `{"name":"Gabriel Barbosa"}` |
| Which players are at Flamengo in the snapshot? | `search_players` | `{"club":"Flamengo"}` |
| Derbies in 2023? | `search_matches` | `{"season":2023,"derbies":true}` |
| What competitions has Palmeiras played in? | `team_profile` | `{"team":"Palmeiras"}` |
| Best home record? | `statistics` | `{"venue":"home","sort":"win_rate"}` |
| Top Brazilian players? | `search_players` | `{"nationality":"Brazil","limit":10}` |
| Compare 2018 and 2019 | `statistics` | `{"from":"2018-01-01","to":"2019-12-31"}` |
| Show corners and shots | `search_matches` | `{"source":"BR-Football-Dataset.csv","limit":1}` |

Follow-ups such as “What was the score?” use the host's conversation context and the previously returned fixture. The server itself is stateless between tool calls.

## Data quality and interpretation

- All six files are loaded. Original attributes are retained, including UTF-8 names, stadiums, physical attributes and skills. Responses use lowercase, accent-insensitive team identifiers; source spellings remain in `attributes`.
- Normalization handles accents (including decomposed characters), case, state suffixes, abbreviations and explicit aliases. Distinct clubs such as América-MG/América-RN, Botafogo-RJ/Botafogo-PB and Flamengo-RJ/Flamengo-PI remain separate. The curated alias and derby lists are extensible, not universal.
- Overlapping matches merge by competition, season, date and normalized home/away teams. Identical-score fixtures within one day merge across sources to accommodate UTC/local dates. The extended dataset's missing season is resolved from a matching explicit-season fixture when possible, including the 2020 season's 2021 matches. Otherwise its calendar year is used.
- Unplayed Brasileirão fixtures can be enriched by a later source's completed result for the same oriented pairing and season, including rescheduling. The match ID stays stable while its date becomes the completed fixture date. This rule is restricted to the supplied league's single home fixture per pairing/season; it is not applied to cup ties.
- Conflicting scores retain the first source's result and emit warnings. Priority is Brasileirão, Copa do Brasil, Libertadores, extended statistics, historical Brasileirão. All participating sources' raw fields remain available. Source filtering selects canonical matches with that provenance, not a raw source-only recalculation.
- Missing scores remain JSON `null` and never count as 0–0 draws. The undated/unseasoned Libertadores fixture remains searchable with an empty date and season 0, and is excluded from date-range searches. Malformed non-missing dates or scores fail loading.
- League tables use 3 points per win and 1 per draw. Ties sort by points, wins, goal difference, goals scored, then identifier. Official deductions and later tie-breakers are unavailable. Completeness must be checked before claiming an official champion or relegation; 2023 data is partial. The complete 2019 table produces Flamengo's 90 points across 38 games.
- Cup stage mapping uses the supplied file's season-specific numbering. The incomplete 2021 cup data stops at the round of 16. Extended matches lack cup stages and remain available via ordinary match queries. Knockout legs can be inspected, but group membership, bracket progression, shootout winners and individual goalscorers cannot be recovered reliably. These are reported as unavailable rather than fabricated.
- FIFA data is a historical snapshot, with some Brazilian clubs/players absent. A team profile may therefore contain matches but no linked players. No current-roster claim is made.

## Attribution

For demo/non-commercial use as requested. The data remains under its source licenses; no ownership of the datasets is claimed.

| Files | Source | License |
|---|---|---|
| Brasileirão, Copa do Brasil, Libertadores | [ricardomattos05](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| BR-Football-Dataset | [cuecacuela](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 Public Domain |
| novo_campeonato_brasileiro | [macedojleo](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| fifa_data | [youssefelbadry10](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

## Verification

```sh
go test ./...
go test -race ./...
go vet ./...
go test -run '^$' -bench BenchmarkAggregate -benchmem
```

Tests cover all six real datasets, 24 question-to-tool scenarios, known league totals, exact synthetic win/draw/loss calculations, source/date/season reconciliation, pending results, normalization, UTF-8, date validation, cup finals, player filters, graph traversal, pagination, CSV errors and MCP initialization/discovery/calls/errors. Query scenarios check the two-second lookup budget after loading; the benchmark measures full-dataset aggregation. Tests include Given/When/Then-style scenarios without requiring an external BDD framework.

If your environment restricts the default Go cache, set `GOCACHE` to a writable directory when running the commands above.
