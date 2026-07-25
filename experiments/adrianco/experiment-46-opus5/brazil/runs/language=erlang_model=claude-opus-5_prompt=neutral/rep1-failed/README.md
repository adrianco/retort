# Brazilian Soccer MCP Server (Erlang/OTP)

An MCP (Model Context Protocol) server that answers natural language questions about
Brazilian soccer from six Kaggle data sets, implemented in Erlang/OTP with no
dependencies outside the standard library.

The six CSV files are loaded into an in-memory knowledge graph (ETS) at start-up:
**17,276 matches**, **501 teams**, **18,207 players**, **36,917 graph nodes** and
**113,420 edges**, built in about 3 seconds. Queries answer in milliseconds.

```
$ ./_build/default/bin/br_soccer_mcp ask "Who won the 2019 Brasileirao?"
2019 Brasileirão Série A Final Standings (calculated from matches):
1. Flamengo - 90 pts (28W, 6D, 4L) 86:37 - Champion
2. Santos - 74 pts (22W, 8D, 8L) 60:33
3. Palmeiras - 74 pts (21W, 11D, 6L) 61:32
...
17. Cruzeiro - 36 pts (7W, 15D, 16L) 27:46 - Relegated
```

---

## Quick start

Requires Erlang/OTP 27 or later (developed on OTP 29) and rebar3.

```bash
rebar3 escriptize            # build ./_build/default/bin/br_soccer_mcp
rebar3 test                  # escriptize + eunit + common test (150 tests)

./_build/default/bin/br_soccer_mcp info      # what is loaded
./_build/default/bin/br_soccer_mcp demo      # answer all 28 sample questions
./_build/default/bin/br_soccer_mcp ask "Which team has the best away record?"
./_build/default/bin/br_soccer_mcp call standings '{"season":2019}'
./_build/default/bin/br_soccer_mcp serve     # MCP server on stdin/stdout
```

The data directory is found automatically by walking up from the working directory;
override it with `BR_SOCCER_DATA_DIR=/path/to/data/kaggle`.

### Connecting an MCP client

The server speaks JSON-RPC 2.0 over the stdio transport, so any MCP client can launch
it. For Claude Desktop / Claude Code the configuration is:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/_build/default/bin/br_soccer_mcp",
      "args": ["serve"],
      "env": { "BR_SOCCER_DATA_DIR": "/absolute/path/to/data/kaggle" }
    }
  }
}
```

A session looks like this (newline delimited JSON, one message per line):

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"ask","arguments":{"question":"Show me all derbies in 2023"}}}' \
  | ./_build/default/bin/br_soccer_mcp serve
```

---

## What the server exposes

### Tools (20)

| Tool | Answers |
|------|---------|
| `ask` | A natural language question, routed to the tool below that fits it |
| `search_matches` | Matches by team, opponent, home/away, competition, season, date range |
| `head_to_head` | Complete record between two clubs, with the derby name if there is one |
| `team_stats` | W/D/L, goals, points, win rate; per season, per competition, home or away |
| `team_profile` | Everything about a club: per competition, per season, rivals, squad |
| `standings` | League table computed from the results; champion and relegated teams |
| `team_rankings` | Best home/away record, most goals, best defence, ... |
| `competition_stats` | Goals per match, home advantage, biggest win, top scorers |
| `compare_seasons` | Two seasons side by side |
| `biggest_wins` | Largest winning margins, filterable |
| `search_players` | FIFA data by name, nationality, club, position, rating, age |
| `player_profile` | One player with attributes, and his club's match record |
| `club_squad` | A club's players, best rated first |
| `players_by_club` | Players grouped by club with counts and average rating |
| `derbies` | The traditional clássicos and their fixtures |
| `list_teams` | Teams, filterable by competition, season, state or search string |
| `list_competitions` | Competitions and season coverage |
| `dataset_summary` | Files, counts, graph size, load time |
| `graph_neighbors` | Neighbours of a knowledge graph node |
| `graph_path` | Shortest path between two nodes |

Every tool call returns both a text block and `structuredContent`, so a model can read
the prose and a program can use the data.

### Resources

`soccer://datasets`, `soccer://competitions`, `soccer://teams`,
`soccer://graph-schema`, `soccer://sample-questions`.

### Prompts

`soccer_question` (answer a question with the tools) and `scouting_report`
(summarise a club).

### The knowledge graph

```
match  -home_team->      team          team   -played_in->    competition
match  -away_team->      team          team   -based_in->     state
match  -in_competition-> competition   team   -from_country-> country
match  -in_season->      season        player -plays_for->    team
match  -at_venue->       venue         player -nationality->  country
```

Node ids survive JSON (`team:flamengo`, `player:158023`, `season:2019`), so a model can
walk the graph itself:

```
$ ./_build/default/bin/br_soccer_mcp call graph_path \
    '{"from":"player:158023","to":"competition:libertadores"}'
Path (4 hops):
  -[start]-> L. Messi (player:158023)
  -[nationality]-> Argentina (country:argentina)
  -[nationality]-> J. Sand (player:152912)
  -[plays_for]-> Deportivo Cali (team:deportivo-cali)
  -[played_in]-> Copa Libertadores (competition:libertadores)
```

---

## Architecture

```
                   ┌─────────────────────────────────────────────┐
 MCP client ─stdio─▶ br_mcp_stdio → br_mcp_server (JSON-RPC 2.0) │
                   │                       │                     │
                   │               br_mcp_tools (catalogue)      │
                   │                 │            │              │
                   │        br_nl (NL router)     │              │
                   │                 └──────▶ br_query ─── br_format
                   │                              │              │
                   │                     br_store (ETS) + br_graph
                   │                              ▲              │
                   │   br_loader ─ br_csv ─ br_names ─ br_text/br_date
                   └─────────────────────────────────────────────┘
```

| Module | Role |
|--------|------|
| `br_csv` | RFC-4180 reader: quoted fields, embedded newlines, CRLF, BOM |
| `br_text` | UTF-8 normalisation: accent folding, case folding, fast trim |
| `br_date` | `2023-09-24`, `2012-05-19 18:30:00` and `29/03/2003` |
| `br_names` | Team/competition canonicalisation and the club registry |
| `br_loader` | The six files → `#match{}` / `#player{}` records |
| `br_store` | `gen_server` owning the ETS tables; dedupe and indexing |
| `br_graph` | Labelled property graph (nodes, edges, BFS paths) |
| `br_query` | Every query and aggregation; returns plain maps |
| `br_format` | Human readable rendering (what the model reads) |
| `br_nl` | Keyword based question → tool routing |
| `br_json` | JSON on OTP's `json` module, with atom/UTF-8 normalisation |
| `br_mcp_tools` | Tool catalogue: JSON Schema + handler + renderer |
| `br_mcp_server` | JSON-RPC 2.0 and the MCP methods |
| `br_mcp_stdio` | stdio transport (logging is redirected to stderr) |
| `br_soccer` | CLI entry point (`serve`, `ask`, `call`, `demo`, `tools`, `info`) |

Reads go straight to ETS from the calling process, so queries are concurrent and the
`gen_server` is only involved in loading.

---

## Data handling

### Team names

The five match files spell the same club in at least four ways, and the same short name
can mean different clubs. Canonicalisation therefore normalises the spelling, splits off
a trailing region code (a Brazilian state such as `SP` or a CONMEBOL country code such as
`URU`), strips generic club-type affixes (`FC`, `EC`, `Esporte Clube`, ...), and looks the
result up in a registry of ~100 clubs with *strong* aliases (identify a club on their own)
and *weak* aliases (only together with the club's state).

```
"Palmeiras-SP"  "Palmeiras - SP"  "Sociedade Esportiva Palmeiras"  →  palmeiras
"Atlético - MG"  "Atletico Mineiro"                                →  atletico-mg
"Atlético - GO"                                                    →  atletico-go
"Atlético - PR"  "Athletico Paranaense"                            →  athletico-pr
"América - MG"  ≠  "América - RN"        "Flamengo-RJ"  ≠  "Flamengo - PI"
"Nacional (URU)" = "Nacional-URU"        ≠  "Nacional (PAR)"
```

Clubs outside the registry get a deterministic slug that keeps the region, so they still
merge across files and can never collide with a registered club.

### Merging the files

The same fixture appears in up to three files. `#match.id` is derived from competition,
season and the two canonical team ids (plus the date for cup ties, which can repeat within
a season), so duplicates merge instead of double counting: **23,954 match rows → 17,276
matches, 6,676 merged, 2 invalid**. The first source wins per field and later sources only fill gaps -
which is how a 2019 Brasileirão match gets its shot and corner counts from
`BR-Football-Dataset.csv` while keeping its round number from `Brasileirao_Matches.csv`.

### Seasons

`BR-Football-Dataset.csv` has no season column. For the league competitions a match played
in January or February belongs to the previous season - the pandemic-shifted 2020
Brasileirão finished in February 2021.

### Known gaps in the source data (not hidden by the server)

* 2023 Serie A has 377 of 380 matches, 2009 has 379, and 2015 carries one stray non-league
  fixture. `standings` reports `complete: false` for those seasons and does not name a
  champion or relegated teams.
* Two 2019 Copa do Brasil rows in `Brazilian_Cup_Matches.csv` list `Bragantino - PA` as
  both home and away (a lost state suffix). They are counted as invalid and dropped.
* FIFA 19 did not license every Brazilian club, so Flamengo, Palmeiras, Corinthians and
  São Paulo have match data but no squad, and the licensed clubs' player names are
  scrambled in the source. Tools say so instead of returning an empty list silently.
* Counts are always "in this data set", never all-time.

---

## Tests

`rebar3 test` runs 150 tests: 74 EUnit unit tests and 76 Common Test acceptance tests.
The acceptance suites are written as Given/When/Then scenarios (`test/bdd.erl`), so the
Common Test log reads like the Gherkin in the specification:

```
=== Feature: Competition Queries ===
  Scenario: Who won the 2019 Brasileirao?
    Given the match data is loaded
    When I request the 2019 standings
    Then Flamengo should be champion with 90 points
    And Santos and Palmeiras should follow on 74 points
```

| Suite | Covers |
|-------|--------|
| `match_queries_SUITE` | Search by team, season, competition, date range; dedupe |
| `team_queries_SUITE` | Records, home/away splits, head-to-head, profiles, rankings |
| `player_queries_SUITE` | Player search, profiles, squads, cross-file joins |
| `competition_queries_SUITE` | Standings, champions, relegation, coverage |
| `statistics_SUITE` | Goals per match, home advantage, biggest wins, graph traversal |
| `data_integrity_SUITE` | All six files, row counts, merge accounting, UTF-8, graph |
| `mcp_protocol_SUITE` | initialize, tools, resources, prompts, batches, errors |
| `mcp_stdio_SUITE` | The built escript driven as a child process over stdio |
| `sample_questions_SUITE` | 28 sample questions, routing and the latency budgets |

Unit tests cover the parts that decide whether the data is right: CSV edge cases, date
formats, accent folding, the name registry (including the clubs that must *not* merge)
and the graph traversal.

Correctness is checked against reality where it can be: the computed 2019 Brasileirão
table matches the real one (Flamengo 90 points, Cruzeiro/CSA/Chapecoense/Avaí relegated),
as do the champions of 2016, 2017, 2018 and 2022.

Measured on the reference machine: simple lookups 0.3-25 ms, aggregate queries (standings,
league-wide statistics, rankings over every match) 6-65 ms - against budgets of 2 s and
5 s. `rebar3 dialyzer` is clean.

---

## Data sources

Kaggle data can't be downloaded without an account so these (freely available with
attribution) data sets have been downloaded for use here:

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

## Specification

[TASK.md](TASK.md) (identical to [brazilian-soccer-mcp-guide.md](brazilian-soccer-mcp-guide.md))
