# Brazilian Soccer MCP Server (Erlang)

An [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server that
exposes a knowledge graph over Brazilian soccer data — matches, teams,
competitions and FIFA players — so an LLM can answer natural-language questions
about them. It is written in pure Erlang/OTP with **no third-party
dependencies**: JSON is handled by the OTP 27+ built-in `json` module, and the
CSV parser, knowledge graph and JSON-RPC stdio transport are all implemented
here.

The full requirements are in [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

---

## What it does

On startup the server parses the six bundled CSV files (~24,000 matches across
five competitions and ~18,000 FIFA players) into two in-memory ETS tables and
then speaks MCP over stdio. It answers questions in all five required
categories — match lookups, team queries, player queries, competition
standings and statistical analysis — through seven tools.

The calculated 2019 Brasileirão table matches the specification's worked
example exactly:

```
Brasileirão Série A 2019 — final standings (calculated from 380 matches):
1. Flamengo — 90 pts (28W 6D 4L, GF 86 GA 37, GD +49)  Champion
2. Palmeiras — 74 pts (21W 11D 6L, GF 61 GA 32, GD +29)
3. Santos — 74 pts (22W 8D 8L, GF 60 GA 33, GD +27)
...
```

---

## Build, test, run

Requires Erlang/OTP 27+ (built and tested on OTP 29) and `rebar3`.

```sh
rebar3 compile        # compile
rebar3 eunit          # run the test suite (22 tests)
rebar3 escriptize     # build the standalone ./_build/default/bin/bsoccer binary
```

Run the server (speaks MCP/JSON-RPC on stdin/stdout):

```sh
./_build/default/bin/bsoccer
```

Smoke-test without an MCP client — loads the data, prints a summary and runs a
few demo queries:

```sh
./_build/default/bin/bsoccer --selftest
```

By default it loads CSVs from `data/kaggle/`. Override with a path argument or
the `BSOCCER_DATA_DIR` environment variable.

### Connecting an MCP client

Point any MCP client (e.g. Claude Desktop) at the escript:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/_build/default/bin/bsoccer"
    }
  }
}
```

Or drive it manually — newline-delimited JSON-RPC, one message per line:

```sh
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019}}}' \
  | ./_build/default/bin/bsoccer
```

---

## Tools

| Tool | Answers questions like | Key arguments |
|------|------------------------|---------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?" | `team`, `opponent`, `competition`, `season`, `season_from`/`season_to`, `date_from`/`date_to`, `venue`, `limit` |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" | `team1`, `team2`, `competition` |
| `team_record` | "What is Corinthians' home record in 2022?" | `team`, `season`, `competition`, `venue` |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" | `season` (required), `competition`, `limit` |
| `search_players` | "Find all Brazilian players", "Who are the highest-rated players at Flamengo?" | `name`, `nationality`, `club`, `position`, `min_overall`, `sort`, `limit` |
| `match_statistics` | "What's the average goals per match?", "Show me the biggest wins" | `team`, `competition`, `season`, `season_from`/`season_to` |
| `data_summary` | "What data is available?" | — |

Each tool returns a human-readable answer (in the format the spec illustrates)
as MCP `text` content, plus a machine-readable `structuredContent` payload.

---

## Architecture

| Module | Responsibility |
|--------|----------------|
| `bsoccer_csv` | Minimal RFC-4180 CSV reader (quoted fields, BOM, CRLF). |
| `bsoccer_util` | Normalisation: team-name cleaning/keys, accent folding, multi-format date parsing, lenient goal parsing. |
| `bsoccer_data` | gen_server that loads all CSVs into the `bsoccer_matches` / `bsoccer_players` ETS tables (one canonical match schema across sources). |
| `bsoccer_query` | Query + answer-formatting layer (the seven capabilities). |
| `bsoccer_mcp` | MCP / JSON-RPC 2.0 protocol: `initialize`, `tools/list`, `tools/call`, `ping`, notifications. Transport-agnostic and unit-tested directly. |
| `bsoccer_cli` | escript entry point + the newline-delimited JSON-RPC stdio loop. |

### Handling the data-quality challenges

The specification calls out three messy realities, each addressed explicitly:

- **Team-name variations** — names carry state/country suffixes
  (`Palmeiras-SP`, `Nacional (URU)`, `América - MG`) and accents (`Grêmio`).
  Every name is reduced to a canonical *key* (suffix-stripped, accent-folded,
  lower-cased, alias-merged) used for matching, while a clean display name is
  kept for output.
- **Overlapping sources** — the same season appears in full in up to three
  files, each spelling teams slightly differently. Aggregates (standings,
  records, head-to-head, statistics) **canonicalise** by bucketing on
  `{competition, season}` and keeping only the single highest-priority source
  present, so each real match is counted exactly once with consistent naming.
  (This is why the 2019 table comes out at the correct 380 matches / 90 points
  rather than a triple-counted total.)
- **Multiple date formats & UTF-8** — ISO, ISO+time and Brazilian
  `DD/MM/YYYY` dates are all parsed, and accented text round-trips correctly
  through the JSON stdio transport.

### Performance

Data loads in ~1.5s at startup; queries scan the ETS tables and return in tens
of milliseconds — comfortably inside the spec's <2s (simple) / <5s (aggregate)
budgets.

---

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) data sets have been downloaded for use here:

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
