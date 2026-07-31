# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that exposes a **knowledge graph of Brazilian
soccer** built from the six Kaggle datasets in `data/kaggle/`. It answers natural
language questions about matches, teams, players, competitions and statistics through
24 MCP tools, 4 resources and 2 prompts.

Implements the specification in [`TASK.md`](TASK.md) (also `brazilian-soccer-mcp-guide.md`).

```
$ brazilian-soccer-mcp call competition_standings competition=brasileirao season=2019
2019 Brasileirão final standings (calculated from matches):
1. Flamengo (RJ) - 90 pts (28W, 6D, 4L) GF 86 GA 37 GD +49 - Champion
2. Santos (SP) - 74 pts (22W, 8D, 8L) GF 60 GA 33 GD +27
3. Palmeiras (SP) - 74 pts (21W, 11D, 6L) GF 61 GA 32 GD +29
...
17. Cruzeiro (MG) - 36 pts (8W, 12D, 18L) GF 33 GA 51 GD -18 - Relegated
```

---

## Quick start

```bash
python -m venv venv && source venv/bin/activate
pip install -e ".[test]"

brazilian-soccer-mcp summary                     # dataset coverage report
brazilian-soccer-mcp tools                       # list the 24 tools + arguments
brazilian-soccer-mcp call head_to_head team_a=Flamengo team_b=Fluminense
brazilian-soccer-mcp call competition_standings season=2019 --json
brazilian-soccer-mcp serve                       # run the MCP server on stdio

pytest                                           # 529 tests, ~7 seconds
```

Requires Python 3.11+ and the `mcp` SDK — the only runtime dependency, since the data
layer uses nothing but the standard library.

### Connecting an MCP client

```jsonc
// claude_desktop_config.json / .mcp.json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "brazilian-soccer-mcp",
      "args": ["serve"]
    }
  }
}
```

Or without installing the console script:
`{"command": "python", "args": ["-m", "brazilian_soccer.server"]}`.
Point the server at a different copy of the CSVs with the
`BRAZILIAN_SOCCER_DATA_DIR` environment variable.

---

## What the server exposes

### Tools (24)

| Area | Tools |
|------|-------|
| **Matches** | `search_matches`, `head_to_head`, `find_derbies` |
| **Teams** | `team_stats`, `team_profile`, `compare_teams`, `best_records`, `top_scoring_teams` |
| **Competitions** | `competition_standings`, `competition_champion`, `relegated_teams`, `competition_stats`, `biggest_wins`, `compare_seasons` |
| **Players** | `search_players`, `player_profile`, `club_squad`, `brazilian_club_squads` |
| **Meta / graph** | `resolve_team`, `list_teams`, `list_competitions`, `dataset_summary`, `graph_neighbors`, `position_groups` |

Every tool returns an answer already rendered in the layouts TASK.md specifies, so an
LLM can quote it directly. The CLI's `--json` flag returns the same information as
structured data.

### Resources

`soccer://datasets`, `soccer://competitions`, `soccer://teams`, `soccer://graph/schema`
— the same information as JSON, for clients that prefer to read rather than call.

### Prompts

`analyze_team(team)` and `season_review(competition, season)` — ready-made tool-use plans.

---

## Architecture

```
CSV files ──► loaders ──► TeamRegistry ──► KnowledgeGraph ──► queries ──► formatting
                                                │                 │           │
                                                └──── indexes ─────┴──► tools ─┴──► server (MCP)
                                                                          └──► cli
```

| Module | Responsibility |
|--------|----------------|
| `config.py` | Dataset catalogue (file, licence, competitions) and data directory resolution |
| `text.py` | Accent folding, name tokenising, state/country suffix splitting, date & number parsing |
| `teams.py` | Canonical club registry — the cross-dataset identity layer |
| `models.py` | `Team`, `Match`, `Player`, `TeamRecord`, `StandingRow`, `HeadToHead` |
| `loaders.py` | One reader per CSV, all producing the same intermediate row |
| `graph.py` | Nodes, typed edges, indexes, cross-source de-duplication, load report |
| `queries.py` | Search, head-to-head, records, standings, champions, statistics, players |
| `formatting.py` | Renders results in the answer formats from the specification |
| `tools.py` | Transport-independent tool layer (`call_tool`) shared by server, CLI and tests |
| `server.py` | MCP binding: tools, resources, prompts |
| `cli.py` | `serve`, `tools`, `summary`, `call` |

The knowledge graph is built once per process (~0.9 s for 43k rows) and cached; the
cache key includes each CSV's size and mtime, so pointing the server at different data
rebuilds automatically instead of serving a stale graph.

### Knowledge graph shape

```
match  --home_team-->      team          season --of_competition--> competition
match  --away_team-->      team          team   --competed_in-->    competition
match  --in_competition--> competition   player --plays_for-->      team
match  --in_season-->      season        match  --played_at-->      venue
```

35,569 nodes · 91,762 edges · traversable in both directions through `graph_neighbors`
(`team:flamengo-rj`, `competition:serie-a`, `player:190871`, …).

---

## The two hard problems, and how they are solved

### 1. Club identity across five spellings

The same club appears as `Atletico-MG`, `Atlético-MG`, `Atlético - MG`,
`Atletico Mineiro` and `Atlético Mineiro`; as `Bahia-BA`, `Bahia - BA` and `EC Bahia`;
as `Nacional (URU)` and `Nacional-URU`. Meanwhile `Botafogo` exists in RJ, SP **and**
PB, `América` in MG and RN, and `River Plate` in both Argentina and Uruguay.

Resolution runs in three tiers:

1. **Curated registry** — 158 clubs with explicit ids, states/countries, aliases and
   nicknames. A club only claims its bare, unqualified name when that name is
   unambiguous, which is why `Botafogo` → Botafogo-RJ but `América` alone does not
   resolve.
2. **Observed clustering** — every raw spelling seen while loading is bucketed by
   `(match_key, qualifier)`, where `match_key` strips club-type noise (`EC`, `FC`,
   `Clube`, `do`, …) so `"EC Bahia"` and `"Bahia - BA"` share the key `bahia`. An
   unqualified name joins a qualified cluster only when exactly one qualifier exists
   for that key.
3. **Fuzzy search** — user-facing lookup over names, aliases and nicknames, so
   `Flamengo`, `flamengo rj` and `Mengão` all work from an LLM's tool call.

Nationality is inferred, not assumed: a club seen in Serie A/B/C or the Copa do Brasil
is Brazilian; a Libertadores-only club is not. That is what stops FIFA's
`FC Barcelona` colliding with Barcelona SC of Ecuador.

### 2. The datasets overlap heavily

Serie A 2014–2019 appears in **three** of the provided files. Counting those rows three
times would corrupt every table, so fixtures are merged on
`(competition, home club, away club)`:

* **Serie A** merges per season — it has been a pure double round robin since 2003, so
  an ordered pair meets exactly once a season. That is how Goiás–Corinthians 2022 stays
  one fixture even though one file records the original 15 Oct date (no score) and
  another the 29 Oct replay.
* **Everything else** merges by date proximity, which keeps genuinely separate meetings
  apart. The two legs of a cup tie already differ by home/away order.

The merged record keeps the highest-priority source's score — the two dedicated
Brasileirão files agree on 100 % of overlapping scores, while the extended-stats file
disagrees on a handful, so it ranks last — plus the union of every source's extra
statistics. `Match.sources` records which files contributed.

**Result: 23,954 raw match rows → 16,789 distinct matches (7,163 duplicates merged,
2 rejected).**

The strongest evidence this is right is structural: 18 of 21 Serie A seasons come out
as exact `n × (n−1)` round robins with every ordered pair appearing exactly once, and
the calculated tables reproduce the historical record — Flamengo 90 pts in 2019
(28W 6D 4L), Cruzeiro 100 pts in 2003, Corinthians 81 in 2015, Palmeiras 81 in 2022,
and the correct four relegations in both 2019 and 2020.

---

## Data coverage

| Competition | Matches | Seasons |
|---|---|---|
| Campeonato Brasileiro Série A | 8,403 | 2003–2023 |
| Campeonato Brasileiro Série B | 3,677 | 2014–2023 |
| Campeonato Brasileiro Série C | 1,807 | 2014–2023 |
| Copa do Brasil | 1,647 | 2012–2023 |
| Copa Libertadores | 1,255 | 2013–2022 |

396 clubs with matches · 18,207 FIFA players · 300 players (15 squads of 20) linked to
a club in the match graph.

### Known data gaps

These are properties of the source files, not of the implementation. The server reports
them rather than papering over them, and each one is pinned by a test.

* **No goalscorer or lineup data anywhere.** Individual top scorers are therefore *not*
  derivable; `top_scoring_teams` answers the team-level version of the question.
* **FIFA 19 omits unlicensed clubs.** Flamengo, Palmeiras, Corinthians, São Paulo and
  Vasco have no player rows, so `club_squad` / `search_players` return an explicit
  explanation for them (their matches are all present). 15 Brazilian clubs do have
  squads.
* **Copa do Brasil 2021–2023 finals are missing.** The cup file stops after the 2021
  round of 16 and the extended-stats file carries no round column, so
  `competition_champion` says "the dataset records no final" instead of guessing. The
  same applies to the 2021 and 2022 Libertadores finals.
* **Finals decided on penalties** (Libertadores 2013, Copa do Brasil 2015 and 2017)
  report the aggregate tie and state that the shoot-out is not in the data.
* **Serie A 2009** is missing one Flamengo–Botafogo fixture, which is why the
  calculated table puts Internacional first rather than Flamengo.
* **Serie A 2015/2016 and Serie B** contain a handful of state-championship rows
  mislabelled by the extended-stats file (e.g. Brasília FC vs CA Taguatinga).
* **Serie A 2023** comes only from the extended-stats file and has 377 of 380 matches.
* Two Copa do Brasil 2019 rows list `Bragantino - PA` as *both* home and away; they are
  rejected at load time and counted in the load report.

---

## Testing

529 tests, ~7 seconds, 96 % statement coverage.

```bash
pytest                                    # everything
pytest tests/test_bdd_scenarios.py -v     # 77 BDD scenarios
pytest tests/test_sample_questions.py -v  # the specification's sample questions
pytest --cov=brazilian_soccer --cov-report=term-missing
```

### BDD (Given / When / Then)

`tests/features/*.feature` holds Gherkin scenarios run by `pytest-bdd`, built on a
small reusable step vocabulary so new scenarios need no new Python:

```gherkin
Feature: Match Queries

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I call the "head_to_head" tool with {"team_a": "Flamengo", "team_b": "Fluminense"}
    Then the answer contains "Fla-Flu"
    And the field "played" is at least 30
    And every returned match has a date, a score and a competition
```

Feature files cover match queries, team queries, player queries, competition queries,
statistics, data-quality handling, graph traversal and the specification's latency
budgets. Every step goes through the same `call_tool` entry point the MCP server uses.

### Other test layers

| File | What it checks |
|------|----------------|
| `test_text.py` | Accents, name tokenising, qualifier splitting, the three date formats |
| `test_teams.py` | Variants that must merge, homonyms that must not, FIFA club linking |
| `test_loaders.py` | The row count TASK.md quotes for each CSV, per-file quirks, cup round naming |
| `test_graph.py` | Round-robin completeness per season, merge rules, node/edge integrity |
| `test_queries.py` | Champions, relegations and records checked against the historical record |
| `test_tools.py` | Every tool answers, is documented, and fails gracefully |
| `test_mcp_server.py` | In-process MCP client **and** a real stdio JSON-RPC session |
| `test_sample_questions.py` | 31 questions from the specification, end to end |
| `test_robustness.py` | Missing data directory, empty graph, a hand-written mini dataset |
| `test_formatting.py`, `test_models.py`, `test_cli.py` | Renderers, derived properties, CLI plumbing |

### Success criteria from the specification

| Criterion | Status |
|---|---|
| Search and return match data from all provided CSV files | ✅ all 5 match files, 16,789 merged matches |
| Search and return player data | ✅ 18,207 FIFA players |
| Calculate basic statistics (wins, losses, goals) | ✅ `team_stats`, `competition_stats`, `best_records` |
| Compare teams head-to-head | ✅ `head_to_head`, `compare_teams` |
| Handle team name variations correctly | ✅ three-tier resolution, 50+ dedicated tests |
| Return properly formatted responses | ✅ renderers match the specification's example layouts |
| Simple lookups < 2 s, aggregates < 5 s, no timeouts | ✅ asserted in `performance.feature` (typical: 1–30 ms) |
| All 6 CSV files loadable and queryable | ✅ `test_loaders.py` asserts the documented row counts |
| At least 20 sample questions answerable | ✅ 31 in `test_sample_questions.py` |
| Cross-file queries work | ✅ `club_squad` joins FIFA squads to match history |

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

Demo / non-commercial use, as stated in the specification.
