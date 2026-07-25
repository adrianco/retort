# Brazilian Soccer MCP Server (Erlang/OTP)

An [MCP](https://modelcontextprotocol.io) server that turns the six provided
Kaggle CSV files into a queryable knowledge graph of Brazilian football and
exposes it to an LLM as 14 tools. Implemented in Erlang/OTP with **no external
dependencies** — JSON comes from the OTP 27+ `json` module, storage from ETS.

```
$ ./_build/default/bin/bsmcp summary
Brazilian soccer knowledge graph: 16695 matches, 392 teams, 18207 players
23954 source rows loaded in 2466 ms from data/kaggle
...
$ ./_build/default/bin/bsmcp call standings '{"competition":"serie a","season":2019}'
2019 Brasileirão Série A final standings (calculated from 380 matches)
  1. Flamengo-RJ               90 pts (28W 6D 4L) 86:37 +49 - Champion
  2. Santos-SP                 74 pts (22W 8D 8L) 60:33 +27
  3. Palmeiras                 74 pts (21W 11D 6L) 61:32 +29
...
Relegated: Cruzeiro, CSA, Chapecoense, Avaí
```

Those numbers are calculated from the match results alone and match the
published 2019 table exactly — which is the point of the de-duplication work
described below.

---

## Quick start

Requires Erlang/OTP 27 or later (developed on OTP 29) and rebar3.

```sh
make            # compile + build the executable
make test       # 64 BDD scenarios across 9 Common Test suites
make check      # tests + dialyzer

./_build/default/bin/bsmcp summary                 # what is loaded
./_build/default/bin/bsmcp tools                   # the tool catalogue
./_build/default/bin/bsmcp call head_to_head '{"team_a":"Flamengo","team_b":"Fluminense"}'
./_build/default/bin/bsmcp call standings '{"competition":"serie a","season":2019}' --json
./_build/default/bin/bsmcp serve                   # MCP server on stdin/stdout
```

Register it with an MCP client (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/_build/default/bin/bsmcp",
      "args": ["serve"],
      "env": { "BSMCP_DATA_DIR": "/absolute/path/to/data/kaggle" }
    }
  }
}
```

`BSMCP_DATA_DIR` is optional: the server also finds `data/kaggle` by walking up
from the working directory or from its own installation directory.

---

## What it answers

The tool catalogue is written for a model that has to pick a tool from a natural
language question.

| Tool | Answers questions like |
|---|---|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?", "Find all Libertadores finals" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head", "When did Flamengo last play Corinthians?" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `team_profile` | "What competitions has Palmeiras played in?" |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `league_leaderboard` | "Which team scored the most goals in Serie A 2023?", "Which team has the best away record?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?", "Compare the 2018 and 2019 seasons" |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Atlético Mineiro" |
| `player_profile` | "Who is Neymar?" |
| `club_squad` | "Which players play for Grêmio?" |
| `club_ratings` | "Brazilian players at Brazilian clubs, by average rating" |
| `list_teams` | "Which Botafogo is which?" |
| `dataset_summary` | "What data do you have?" |

Every call returns **both** a `structuredContent` map (for programmatic use) and
a rendered text block in the answer shapes the specification asks for. Failures
come back as `isError: true` with a way forward — an unknown club lists similar
names, a missing season lists the seasons that exist — rather than as a protocol
error, so the model can recover on its own.

Four MCP resources are exposed as well: `bsmcp://dataset/summary`,
`bsmcp://dataset/sources` (provenance and licences), `bsmcp://teams` and
`bsmcp://competitions`.

---

## How it works

```
CSV files ──► bsmcp_csv ──► bsmcp_data ──► ETS knowledge graph ──► bsmcp_query
                              │                                        │
                       bsmcp_names (club identity)              bsmcp_format
                                                                       │
              bsmcp_stdio ──► bsmcp_server (JSON-RPC) ──► bsmcp_tools ──┘
```

| Module | Responsibility |
|---|---|
| `bsmcp_csv` | RFC-4180 reader: quoted fields, embedded commas, CRLF, BOM, short rows |
| `bsmcp_text` | Accent folding, normalisation, the three date formats, `NA`/`-`/`1.0` numbers |
| `bsmcp_names` | Club identity: state suffixes, legal-form words, curated aliases |
| `bsmcp_data` | Loader and ETS graph (match, team and player nodes plus their edges) |
| `bsmcp_query` | Filters, records, tables, leaderboards, player search |
| `bsmcp_format` | Human readable rendering of every result |
| `bsmcp_tools` | Tool catalogue (JSON Schema) and argument coercion |
| `bsmcp_server` | JSON-RPC 2.0 / MCP methods, resources, error mapping |
| `bsmcp_stdio` | Newline delimited JSON transport |
| `bsmcp` | CLI entry point (`serve`, `summary`, `tools`, `call`, `rpc`) |

A gen_server owns public named ETS tables; queries run in the calling process
straight against ETS, so a request never queues behind the loader. Loading takes
~2.5 s for 24k match rows plus 18k players; queries take 0.3–60 ms.

### Club identity

The same club is written five ways across the files, and a bare name can denote
different clubs in different states. Resolution is three steps — peel the state
or country marker, strip legal-form words, then apply a curated alias table that
is *state aware* — and keys that occur with several states stay separate:

```
$ bsmcp call list_teams '{"query":"Atletico"}'
  Atlético Mineiro (MG) - 915 matches; spellings in the data:
      Atletico Mineiro | Atletico-MG | Atlético - MG | Atlético Mineiro - MG | Atlético-MG
  Athletico Paranaense (PR) - 899 matches; spellings in the data:
      Athletico | Athletico Paranaense | Athletico-PR | Atletico - PR | Atlético-PR | ...
  Atlético Goianiense (GO) - 534 matches
  Atlético Acreano (AC) - 46 matches
```

`Botafogo` resolves to the Rio club (the one with the most matches) while
`Botafogo-SP` and `Botafogo - PB` stay distinct; `Flamengo - PI` never collapses
into Flamengo; `EC Internacional SC` (Lages) is not Internacional of Porto
Alegre.

### De-duplicating the sources

The three Série A sources overlap heavily (2012–2019 is in all of them), so a
naive load counts the 2019 season three times and puts Flamengo on 270 points.
Fixtures are keyed on `{competition, season, home, away}` and **merged**, with
the more specific source winning on conflicts:

* the round comes from `Brasileirao_Matches.csv`,
* the stadium from `novo_campeonato_brasileiro.csv`,
* shots, attacks and corners from `BR-Football-Dataset.csv`,
* a score that is `NA` in one file is filled in from another.

Each fixture keeps the list of files it came from. 23,954 source rows collapse
into 16,695 distinct fixtures, and every Série A season from 2003 to 2022 ends
up with the right number of matches, teams and points. The extended-stats file
has no season column, so league fixtures played in January or February (the 2020
season finished in February 2021) are attributed to the season they belong to.

### Refusing to make things up

* A league table is only declared `complete` — and only then names a champion
  and a relegation zone — when every club played the full double round robin.
  2009, 2015 and 2023 are missing fixtures in the sources, so they come back as
  partial tables with no champion.
* A few rows in the extended-stats file carry the wrong tournament label; clubs
  with one or two matches in a 38 round league are reported separately as
  `excluded_teams` instead of polluting the table.
* Goal scorers, line-ups, cards and transfers are in none of the sources; the
  server says so in its `instructions` instead of guessing.
* The FIFA file only carries squads for the clubs the game was licensed for, so
  `club_squad` for Flamengo explains why it is empty and lists the Brazilian
  clubs that do have squads.

---

## Tests

`make test` runs 64 BDD scenarios. Each Common Test case *is* a scenario: it
declares its feature and scenario name and then runs Given/When/Then steps that
show up in the CT HTML log.

```
%%% competition_queries_SUITE: ........     league tables, champions, relegation
%%% data_quality_SUITE: ..........         CSV/dates/accents/name variants/merge
%%% match_queries_SUITE: ........          match search, filters, error recovery
%%% mcp_protocol_SUITE: ..........         handshake, tools, resources, errors
%%% player_queries_SUITE: ........         player search, positions, cross-file links
%%% sample_questions_SUITE: .....          25 sample questions + latency budgets
%%% statistics_SUITE: ......               aggregates and their invariants
%%% stdio_transport_SUITE: .               the real executable driven over a pipe
%%% team_queries_SUITE: ........           records, head-to-head, leaderboards
All 64 tests passed.
```

Correctness is pinned down two ways: against published results (Flamengo's 90
points from 28W/6D/4L in 2019, the four relegations in 2019 and 2020, Cruzeiro's
100 points in 2003, São Paulo's 78 in 2006) and against invariants that survive
a data refresh (wins + draws + losses = played, league goals for = goals
against, home and away splits sum to the total, percentages sum to 100).

Success criteria from the specification:

| Criterion | Status |
|---|---|
| All 6 CSV files loadable and queryable | ✅ 23,954 match rows + 18,207 players |
| Search and return match data | ✅ `search_matches`, `biggest_wins` |
| Search and return player data | ✅ `search_players`, `player_profile`, `club_squad` |
| Calculate statistics (wins, losses, goals) | ✅ `team_stats`, `standings`, `competition_stats` |
| Compare teams head-to-head | ✅ `head_to_head` |
| Handle team name variations | ✅ `bsmcp_names` + `list_teams`, six scenarios in `data_quality_SUITE` |
| Properly formatted responses | ✅ text and structured content on every tool |
| Simple lookups < 2 s | ✅ measured in `sample_questions_SUITE`, worst case 1.2 ms |
| Aggregate queries < 5 s | ✅ measured, worst case 59 ms |
| At least 20 sample questions | ✅ 25, each executed and checked |
| Cross-file queries | ✅ player → club → match record, asserted in two suites |

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

## Specification

[brazilian-soccer-mcp-guide.md](brazilian-soccer-mcp-guide.md) (identical to `TASK.md`).
