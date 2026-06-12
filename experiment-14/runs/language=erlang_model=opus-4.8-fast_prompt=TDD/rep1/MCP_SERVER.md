# Brazilian Soccer MCP Server (Erlang)

An [MCP](https://modelcontextprotocol.io) server that answers natural-language
questions about Brazilian soccer over the Kaggle datasets in `data/kaggle/`.
It speaks JSON-RPC 2.0 over stdio (newline-delimited messages).

## Build

Requires Erlang/OTP 27+ (uses the built-in `json` module) and `rebar3`.

```sh
rebar3 compile          # compile
rebar3 eunit            # run the unit tests
rebar3 escriptize       # build the ./_build/default/bin/bsmcp executable
```

## Run

```sh
./_build/default/bin/bsmcp [data-dir]   # default data-dir: data/kaggle
```

The server loads all datasets on startup (progress is logged to **stderr** so it
never corrupts the protocol on stdout), then serves requests until stdin closes.

### Quick manual check

```sh
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirão","season":2019}}}' \
  | ./_build/default/bin/bsmcp 2>/dev/null
```

### Claude Desktop / MCP client config

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/_build/default/bin/bsmcp",
      "args": ["/absolute/path/to/data/kaggle"]
    }
  }
}
```

## Tools

| Tool | Required args | Optional args | Answers |
|------|---------------|---------------|---------|
| `find_matches` | – | `team`, `opponent`, `home_team`, `away_team`, `season`, `competition`, `limit` | "Show me all Flamengo vs Fluminense matches" |
| `head_to_head` | `team_a`, `team_b` | – | "Compare Palmeiras and Santos head-to-head" |
| `team_record` | `team` | `season`, `competition`, `home_only`, `away_only` | "What is Corinthians' home record in 2022?" |
| `find_players` | – | `name`, `nationality`, `club`, `position`, `min_overall`, `limit` | "Who are the top Brazilian players?" |
| `standings` | `competition`, `season` | – | "Who won the 2019 Brasileirão?" |
| `match_statistics` | – | `competition`, `season`, `team` | "What's the average goals per match?" |

Competition names: **Brasileirão**, **Copa do Brasil**, **Libertadores**
(also **Serie A/B/C** from the extended-statistics dataset).

## How data quality is handled

* **Team names** are normalized (lowercase, accent-free, state/country suffix
  stripped) so `Palmeiras-SP`, `Palmeiras` and `São Paulo`/`Sao Paulo` match.
  A small alias table (`bsmcp_aliases`) keeps the ambiguous clubs distinct —
  `Atlético-MG`, `Atlético-GO` and `Athletico-PR` would otherwise collapse to
  one — and folds the extended dataset's full names (`Atletico Mineiro`,
  `EC Bahia`, `Vasco Da Gama RJ`) onto the same key.
* **Dates** in ISO, `DD/MM/YYYY` and `YYYY-MM-DD HH:MM:SS` forms are all
  normalized to `YYYY-MM-DD`.
* **Overlapping files** (the same fixture appears in several CSVs) are
  de-duplicated by date + teams so head-to-head and standings are not
  double-counted. Standings computed from matches reproduce the real tables
  (e.g. Flamengo win the 2019 Brasileirão with 90 pts, 28W 6D 4L).

### Known limitations

* The provided FIFA dataset is the FIFA 19 snapshot, so club squads reflect
  2018/19 and most Brazilian-league clubs have few entries.
* A handful of lower-division/cup opponents are spelled differently across
  files (e.g. `4 de Julho` vs `4 de Julho EC`) and are not aliased, so they may
  appear twice in unfiltered statistics.

## Architecture

| Module | Responsibility |
|--------|----------------|
| `bsmcp_csv` | RFC-4180-style CSV parser (quotes, CRLF, UTF-8, BOM) |
| `bsmcp_normalize` | Team-name canonicalization and display names |
| `bsmcp_aliases` | Curated club alias → canonical-key table |
| `bsmcp_data` | Per-file row → canonical match/player maps, loading, de-dup |
| `bsmcp_query` | Match/team/player/standings/statistics queries |
| `bsmcp_format` | Human-readable rendering of results |
| `bsmcp_tools` | MCP tool catalog and dispatch |
| `bsmcp_mcp` | JSON-RPC 2.0 request handling + JSON codec |
| `bsmcp_server` | stdio transport and data-store loading |
| `bsmcp` | escript entry point |

All behavior is covered by EUnit tests under `test/` (`rebar3 eunit`).
