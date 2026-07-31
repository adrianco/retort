# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that answers natural-language questions
about Brazilian football, backed by an in-memory knowledge graph built from the
six Kaggle datasets in `data/kaggle/`.

**17,144 de-duplicated matches** (Brasileirão Série A/B/C 2003–2023, Copa do
Brasil 2012–2023, Copa Libertadores 2013–2022), **407 clubs** and **18,207 FIFA
players**, exposed through **22 MCP tools**. The whole dataset loads in ~0.4 s
and every query answers in single-digit milliseconds.

## Quick start

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"

.venv/bin/python -m brazilian_soccer.server        # run the MCP server (stdio)
.venv/bin/python -m brazilian_soccer.cli demo      # answer the spec's sample questions
.venv/bin/python -m pytest                         # 326 tests, ~1.5 s
```

No third-party runtime dependencies beyond the MCP SDK — the data layer is pure
standard library (`csv`, `dataclasses`, dictionaries), which is why load and
query times are what they are.

### Connecting it to Claude Code / Claude Desktop

```jsonc
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "brazilian_soccer.server"],
      "env": { "BRAZILIAN_SOCCER_DATA_DIR": "/absolute/path/to/data/kaggle" }
    }
  }
}
```

`BRAZILIAN_SOCCER_DATA_DIR` is optional; it defaults to `data/kaggle` next to
the package.

## The 22 tools

| Group | Tools |
|---|---|
| Matches | `search_matches`, `head_to_head`, `last_meeting`, `find_derbies` |
| Teams | `team_statistics`, `team_profile`, `compare_teams`, `team_season_trend`, `search_teams` |
| Players | `search_players`, `get_player`, `club_squad`, `players_by_club` |
| Competitions | `standings`, `season_champion`, `relegated_teams`, `competition_bracket` |
| Statistics | `competition_statistics`, `biggest_wins`, `team_rankings`, `compare_seasons`, `dataset_overview` |

Sample output:

```
$ python -m brazilian_soccer.cli standings 2019
2019 Brasileirão Série A standings (calculated from match results):
 1. Flamengo-RJ - 90 pts (28W, 6D, 4L) GF 86 GA 37 GD +49 - Champion
 2. Palmeiras - 74 pts (21W, 11D, 6L) GF 61 GA 32 GD +29
 3. Santos-SP - 74 pts (22W, 8D, 8L) GF 60 GA 33 GD +27
...

$ python -m brazilian_soccer.cli h2h Flamengo Fluminense
Flamengo-RJ vs Fluminense-RJ:
- 2023-11-11: Flamengo-RJ 1-1 Fluminense-RJ (Brasileirão Série A)
...
Head-to-head in dataset: Flamengo-RJ 18 wins, Fluminense-RJ 14 wins, 12 draws (goals 60-48)
```

## Architecture

```
normalization.py  team-name / date / number canonicalisation
models.py         Match, Player, Team, TeamRecord, HeadToHead
loader.py         one reader per CSV -> normalised records
graph.py          KnowledgeGraph: nodes, edges, indexes, de-duplication
queries.py        the analytical API (matches, teams, players, standings, stats)
formatting.py     human-readable rendering
server.py         the MCP tool surface
cli.py            offline driver / demo
```

Each layer depends only on the ones above it, so the analytics are testable as
data and the presentation is testable as strings, with no MCP client involved.

### What the hard parts were

**Team-name normalisation.** The match files contain 725 distinct raw team
strings for 407 actual clubs: `Palmeiras` / `Palmeiras-SP` / `Palmeiras - SP`, `Atletico Mineiro` /
`Atlético-MG`, `A.b.c. - RN` / `ABC`, `Clube Do Remo` / `Remo - PA`. The
normaliser strips accents, drops club-type noise (`FC`, `EC`, `Futebol Clube`,
`Esporte`) and Portuguese connectors, collapses dotted initials, and pulls off
state/country suffixes — but only when they are upper case, so `São Paulo` never
loses "Paulo" while `Botafogo PB` does lose "PB".

Suffixes are *not* simply discarded. Bases that name more than one real club
(`america`, `botafogo`, `nautico`, `santos`, …) keep their region in the key, so
América-MG and América-RN stay distinct, while a bare `Flamengo` still resolves
to the Rio club via a default-region table. An alias table covers what no rule
can reach (`Vasco` = `Vasco da Gama`, `Athletico` = `Atlético Paranaense`).

**Cross-file de-duplication.** `Brasileirao_Matches.csv`,
`novo_campeonato_brasileiro.csv` and `BR-Football-Dataset.csv` all cover Série A
and overlap for 2014–2019; counting those rows twice would double every
standings table. League fixtures de-duplicate on
`(competition, season, home, away)` — in a double round-robin an ordered pair
meets exactly once per season — while cups de-duplicate on the match date, since
two legs are normal there. Duplicates are *merged*, so the stats file can enrich
a row from the schedule file. 6,807 duplicate rows collapse this way, and 15 of
the 18 Série A seasons from 2006 on come out at exactly 380 matches (20 clubs,
no repeated fixture). The three exceptions are source-data artefacts, not
de-duplication failures: 2009 (379) and 2023 (377) are simply missing rows
upstream, and 2015 (381) carries one state-league match that
`BR-Football-Dataset.csv` mislabels as Série A.

Two related data problems had to be handled: the 2020 Brasileirão finished in
February 2021, so `BR-Football-Dataset.csv` rows dated January–March are
attributed to the previous season (otherwise 39 fixtures land in 2021 and never
de-duplicate); and three corrupt source rows are rejected (two `Brazilian_Cup`
rows list `Bragantino - PA` on both sides, and the 2022 Libertadores final is
recorded as `NA,"Flamengo","Athletico","-","-",NA`).

**Saying what the data can't answer.** Standings, champions and relegation are
*calculated from match results* — no source file contains a table — and the tool
output says so. Where a Copa do Brasil final was level on aggregate (2017:
Cruzeiro 1-1 Flamengo), no winner is invented; the finalists and "decided on
penalties" are reported instead. The FIFA file is a FIFA 19 snapshot, so
`get_player("Gabriel Barbosa")` answers "no exact match … closest match:" rather
than quietly describing Gabriel Jesus. There is no goal-scorer or lineup data in
any file, so individual scoring records cannot be derived, and the server
instructions tell the LLM that up front.

### Verified against reality

The derived tables are checked against publicly known outcomes, so a regression
in de-duplication or points arithmetic fails loudly:

| Check | Result |
|---|---|
| 2019 Brasileirão | Flamengo, 90 pts (28W 6D 4L); Santos and Palmeiras 74 | ✅ |
| 2015 / 2017 / 2018 / 2022 champions | Corinthians 81, Corinthians 72, Palmeiras 80, Palmeiras 81 | ✅ |
| 2019 Copa Libertadores final | Flamengo 2-1 River Plate | ✅ |
| 2018 / 2019 / 2020 Copa do Brasil | Cruzeiro, Athletico-PR, Palmeiras | ✅ |
| Série A 2014, 2016-2022 | exactly 380 matches, 20 clubs, no repeated fixture | ✅ |
| Every league season | no `(season, home, away)` fixture appears twice | ✅ |

## Tests

326 tests, written as BDD Given/When/Then scenarios (each step is spelled out in
a comment so a scenario reads top to bottom), run in ~1.5 s:

| File | Covers |
|---|---|
| `test_normalization.py` | name variants, ambiguous clubs, date formats, UTF-8 |
| `test_loader_and_graph.py` | all six files load, de-duplication, indexes, resolution |
| `test_match_queries.py` | Feature: Match Queries (the spec's first scenario) |
| `test_team_queries.py` | Feature: Team Queries (the spec's second scenario) |
| `test_player_queries.py` | Feature: Player Queries + cross-file joins |
| `test_competition_queries.py` | standings, champions, relegation, brackets |
| `test_statistics.py` | goals/match, home-away splits, rankings, biggest wins |
| `test_mcp_server.py` | tool registration, schemas, every tool called, error paths |
| `test_sample_questions.py` | 27 spec sample questions, asked through the MCP layer |
| `test_performance.py` | the spec's <2 s simple / <5 s aggregate budgets |
| `test_cli.py` | demo questions and every CLI subcommand |

Arithmetic is verified two ways: against a hand-computed three-team fixture
(`tiny_graph` in `conftest.py`) where every expected number is written out, and
against the real data via internal consistency (goals for == goals against
league-wide, wins == losses, 38 matches per club) plus the known-outcome table
above.

## Requirements coverage

| Spec requirement | Where |
|---|---|
| Search matches from all provided CSVs | `search_matches`, `loader.py` |
| Search player data | `search_players`, `get_player`, `club_squad` |
| Calculate basic statistics | `team_statistics`, `competition_statistics` |
| Compare teams head-to-head | `head_to_head`, `compare_teams` |
| Handle team name variations | `normalization.py`, `graph.resolve_teams` |
| Properly formatted responses | `formatting.py` (matches the spec's answer layouts) |
| Simple lookups < 2 s / aggregates < 5 s | `test_performance.py` (actual: ~1-20 ms) |
| All 6 CSVs loadable and queryable | `test_loader_and_graph.py` |
| ≥ 20 sample questions answerable | `test_sample_questions.py` (27) |
| Cross-file queries (player + match) | `club_squad` + `team_profile`, `TestCrossFileQueries` |

## Specification

`brazilian-soccer-mcp-guide.md` / `TASK.md`

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
