# Brazilian Soccer MCP Server

An MCP server exposing a knowledge graph over six public Brazilian-soccer
datasets, so an LLM can answer natural-language questions about matches, teams,
players, competitions and aggregate statistics.

Implemented per the specification in `TASK.md` / `brazilian-soccer-mcp-guide.md`.

## Quick start

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python "mcp>=2.0" pytest

.venv/bin/python -m pytest          # 137 tests
.venv/bin/python -m brazilian_soccer.server   # serve on stdio
```

Register with an MCP client (e.g. Claude Desktop / Claude Code):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "brazilian_soccer.server"],
      "cwd": "/absolute/path/to/this/repo"
    }
  }
}
```

Set `BRAZILIAN_SOCCER_DATA_DIR` to point at the CSVs if they are not in
`./data/kaggle`.

The library is usable directly too:

```python
from brazilian_soccer import load_default_graph
graph = load_default_graph()
graph.standings("Serie A", 2019)["champion"]      # 'Flamengo'
graph.head_to_head("Flamengo", "Fluminense")["derby"]   # 'Fla-Flu'
```

## Tools

| Tool | Answers questions like |
|---|---|
| `search_matches` | "What matches did Palmeiras play in 2023?", "Find all Copa do Brasil finals" |
| `head_to_head` | "Show me all Flamengo vs Fluminense matches", "Compare Palmeiras and Santos" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `team_profile` | "What competitions has Palmeiras played in?" |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `competition_summary` | "How did the 2019 Série A compare on goals?" |
| `competition_bracket` | "Show the 2018 Copa Libertadores bracket" |
| `statistics` | "What's the average goals per match in the Brasileirão?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `team_leaderboard` | "Which team has the best away record?", "Who scored most in 2023?" |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Cruzeiro" |
| `player_profile` | "Who is Neymar?" |
| `brazilian_club_squads` | "Which Brazilian clubs have squads in the player data?" |
| `list_teams` | Resolve an ambiguous club name |
| `find_derbies` | "Show me all derbies in 2019" |
| `dataset_overview` | "What data do you have?" |

Every tool returns a formatted, quotable answer **and** the JSON behind it, so
the model can either read the summary or re-aggregate the structured data.
Bad input (unknown club, unknown competition, unparseable date) comes back as
readable text flagged `isError`, with suggestions where possible — never a
traceback.

## Architecture

```
brazilian_soccer/
  names.py       team-name normalisation and alias resolution
  models.py      immutable Match and Player records
  loader.py      one reader per CSV + cross-source de-duplication
  graph.py       KnowledgeGraph: indexes and all query/aggregation logic
  formatters.py  human-readable renderings
  server.py      MCP tool definitions and stdio entry point
```

Pure standard library apart from `mcp` itself. The whole corpus loads in ~1s
into dict indexes; simple lookups are sub-millisecond and full-table aggregates
take a few milliseconds, well inside the specification's 2s / 5s budgets.
Every module opens with a context block explaining what it does and why.

### The three problems that actually mattered

**1. Team-name normalisation is load-bearing in both directions.** The datasets
spell one club many ways (`Palmeiras-SP`, `Palmeiras`, `EC Bahia`, `Vasco Da Gama RJ`,
`Sport Club do Recife`, `América FC (Minas Gerais)`), so names must be folded —
but the state suffix is *not* noise: `Atlético-MG`, `Athletico-PR` and
`Atlético-GO` are three different clubs. `names.py` therefore strips club-type
boilerplate and accents, keeps the region suffix only for base names that are
genuinely ambiguous, and pins the rest with an explicit alias table.

**2. The same match appears in up to three files.** Counting it three times
would triple every goal total. Records are merged on
(competition, season, home, away) with a few days' date tolerance — the same
kick-off is dated a day apart in different files. The highest-priority source
wins for core fields and the others back-fill round, arena, kick-off and shot
statistics. `BR-Football-Dataset.csv` has no season column, and the COVID-delayed
2020 championship finished in February 2021, so league matches dated
January–February are assigned to the previous season.

The de-duplication is what makes the numbers right, and the tests check it the
strict way: every complete 20-team Série A season must come out at exactly 380
matches and 38 per club, and the computed champions match the historical record
(2010 Fluminense, 2016 Palmeiras, 2019 Flamengo on 90 pts from 28W/6D/4L, 2020
Flamengo, 2022 Palmeiras).

**3. Joining players to clubs is ambiguous in a way the data can't resolve.**
`fifa_data.csv` records no country for clubs, so the Argentine River Plate and
the Portuguese Boavista collide with the Brazilian River-PI and Boavista-RJ of
the Copa do Brasil. A squad is treated as a Brazilian club's only if the club
also played a Brazilian domestic competition *and* the squad is majority-Brazilian.

### Known data limitations (surfaced, not papered over)

- **2023 Série A has 377 of 380 matches** — the only source covering that season
  stops three short.
- **2015 Série A has 381** — one misfiled row (a Campeonato Brasiliense match
  tagged `Serie A`).
- FIFA 19 is the player snapshot: several big Brazilian clubs are unlicensed and
  absent (no Flamengo, Palmeiras, Corinthians, São Paulo), and licensed ones use
  placeholder player names. `player_profile` says so and offers near-matches
  rather than pretending a query matched.

There is a test asserting each of these, so a future data refresh that fixes them
fails loudly instead of drifting.

## Tests

BDD scenarios, written in Gherkin in `tests/features.feature` and implemented
one-to-one as pytest functions whose bodies quote the Given/When/Then steps.

```
tests/features.feature                  the specification, readable
tests/conftest.py                       full-corpus and hand-computed mini-league fixtures
tests/test_loading_and_names.py         loading, de-duplication, normalisation
tests/test_queries.py                   match / team / player / competition / statistics
tests/test_mcp_server.py                tool discovery, errors, 24 sample questions
tests/test_performance_and_formatting.py latency budgets and answer formatting
```

Two assertion styles are used deliberately: the mini-league fixture is small
enough to compute by hand and pins the arithmetic exactly, while real-corpus
tests assert either historically-known facts or invariants (wins + draws +
losses == matches, filters honoured, orderings monotonic).

Tool discovery and error handling are verified by launching
`python -m brazilian_soccer.server` as a subprocess and speaking the real MCP
protocol to it over stdio, so the transport and handshake are covered, not just
the registry.

The specification's success criteria are covered explicitly: all six CSVs load
(`test_all_six_datasets_load`), 24 sample questions are answerable
(`SAMPLE_QUESTIONS`), cross-file player+match queries work
(`test_cross_file_query_joins_players_to_match_data`), and the 2s/5s latency
budgets are asserted per tool.

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

Coverage after de-duplication: 16,838 matches across Brasileirão Série A/B/C,
Copa do Brasil and Copa Libertadores (2003–2023), 408 clubs, 18,207 players.
