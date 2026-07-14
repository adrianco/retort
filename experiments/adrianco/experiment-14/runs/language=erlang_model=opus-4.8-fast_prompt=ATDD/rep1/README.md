# Brazilian Soccer MCP Server (Erlang/OTP)

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server,
written in Erlang/OTP, that answers natural-language style questions about
Brazilian soccer — matches, teams, players, competitions and statistics —
over the bundled Kaggle datasets.

The full requirements live in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) /
[`TASK.md`](TASK.md). This README describes what was built and how to use it.

## What was built

A self-contained MCP server (no third-party dependencies — JSON is handled by
the OTP 27+ `json` module) that:

* loads all **six** provided CSV files (≈ 23,850 matches + 18,207 players) into
  ETS at startup (~2 s) and serves read-only queries from memory,
* speaks **MCP over JSON-RPC 2.0** on the stdio transport (`initialize`,
  `tools/list`, `tools/call`, `ping`),
* exposes **seven tools** that cover every capability category in the spec,
* returns both machine-readable `structuredContent` and a human-readable text
  rendering for each tool result,
* normalises team-name variations ("Flamengo" ↔ "Flamengo-RJ", "Sao Paulo" ↔
  "São Paulo") and the three date formats in the data, and is UTF-8 throughout.

### Tools

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `find_matches` | Find matches by team, opponent, competition, season or date range (most recent first) | `team`, `opponent`, `competition`, `season`, `start_date`, `end_date`, `limit` |
| `head_to_head` | Win/draw record and meetings between two teams | `team1`, `team2`, `competition?`, `season?` |
| `team_statistics` | W/D/L, goals, points and win rate for a team (home/away/all) | `team`, `season?`, `competition?`, `venue?` |
| `search_players` | Search FIFA players by name/nationality/club/position, sortable | `name`, `nationality`, `club`, `position`, `min_overall`, `sort_by`, `limit` |
| `competition_standings` | League table calculated from results (3 pts/win) | `competition`, `season`, `limit?` |
| `aggregate_statistics` | Avg goals/match, home/away win rates, biggest wins | `competition?`, `season?` |
| `list_competitions` | Loaded competitions with match counts and seasons | — |

### Example

```
$ echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"competition_standings","arguments":{"competition":"Brasileirão","season":2019,"limit":3}}}' \
    | ./_build/default/bin/bsoccer-mcp data/kaggle

Brasileirão Série A 2019 - Standings:
  1. Flamengo-RJ - 90 pts (28W 6D 4L, GF 86 GA 37)
  2. Palmeiras-SP - 74 pts (21W 11D 6L, GF 61 GA 32)
  3. Santos-SP - 74 pts (22W 8D 8L, GF 60 GA 33)
```

## Architecture

```
bsoccer_app / bsoccer_sup     OTP application + supervisor
  └── bsoccer_data            gen_server: loads the CSVs into two public ETS
                              tables (bsoccer_matches, bsoccer_players)
bsoccer_csv                   dependency-free RFC-4180 CSV reader
                              (quoted commas, escaped quotes, BOM, CRLF)
bsoccer_norm                  team-name / text normalisation (accent folding,
                              state-suffix handling)
bsoccer_query                 the domain logic behind every tool
bsoccer_format                renders results as human-readable text
bsoccer_mcp                   MCP / JSON-RPC protocol layer (handle/1)
bsoccer_stdio                 stdio transport + escript entry point
```

### Design notes

* **Team-name matching.** A bare query ("Flamengo") matches on a
  suffix-stripped key so it finds "Flamengo-RJ"; a *state-qualified* query
  ("Atlético-MG") must match the full name, keeping the three different
  "Atlético" clubs distinct. See `bsoccer_norm:team_matches/2`.
* **No double counting.** Two files cover the Brasileirão and overlap on
  2012–2019. They are labelled so the Série A figures are never doubled:
  `Brasileirao_Matches.csv` → *Brasileirão Série A* (2012–2022);
  `novo_campeonato_brasileiro.csv` → *Brasileirão Série A* for seasons < 2012,
  otherwise *Campeonato Brasileiro (histórico)* (still loadable/queryable).
  Copa do Brasil, Libertadores and the extended BR-Football dataset get their
  own labels. Competition names in queries are resolved to a single canonical
  source.
* **Dates** are normalised to ISO `YYYY-MM-DD` (handling `DD/MM/YYYY` and
  date-time strings); **goals** parse `"3"` and `"3.0"` alike.

## Build, test, run

Requires Erlang/OTP 27+ (developed on OTP 29) and `rebar3`.

```sh
rebar3 compile          # build
rebar3 eunit            # run the acceptance + unit test suites
rebar3 escriptize       # build the ./_build/default/bin/bsoccer-mcp executable
```

Run the server (reads JSON-RPC from stdin, writes responses to stdout):

```sh
./_build/default/bin/bsoccer-mcp data/kaggle
```

To register with an MCP client (e.g. Claude Desktop), point it at the
`bsoccer-mcp` escript with the data directory as its argument.

## Testing approach (ATDD)

The behaviour was developed with executable **Acceptance Test-Driven
Development**. The acceptance suite
([`test/bsoccer_acceptance_tests.erl`](test/bsoccer_acceptance_tests.erl)) is the
executable specification: each scenario drives the system **only** through the
public MCP JSON-RPC interface (`bsoccer_mcp:handle/1`) — encoding a request,
decoding the response — with no back-door access to internals. Scenarios assert
on *what* the system does in the language of the problem domain (find matches
between two teams, team statistics, league standings, search players) using
ground-truth values taken from the datasets (e.g. Flamengo's 90-point 2019
title, 827 Brazilian players, Neymar Jr rated 92). Finer-grained unit tests
([`test/bsoccer_csv_tests.erl`](test/bsoccer_csv_tests.erl),
[`test/bsoccer_norm_tests.erl`](test/bsoccer_norm_tests.erl)) drive the CSV
reader and the name-normalisation internals.

```
$ rebar3 eunit
...
  All 32 tests passed.
```

Performance (measured): one-time data load ≈ 2 s; simple lookups ≈ 10–260 ms;
aggregate queries ≈ 25 ms — comfortably inside the spec's < 2 s / < 5 s targets.

## Data Sources

Kaggle data can't be downloaded without an account so these (freely available
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
