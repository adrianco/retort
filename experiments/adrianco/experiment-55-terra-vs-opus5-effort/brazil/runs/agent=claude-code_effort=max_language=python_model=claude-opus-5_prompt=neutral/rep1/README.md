# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server that answers natural language questions about
Brazilian football by querying a knowledge graph built from the six Kaggle datasets in
`data/kaggle/`. Implementation of the specification in [TASK.md](TASK.md).

```text
16,742 matches   363 clubs   18,207 players   101 stadiums   2003-2023
Brasileirão Série A / B / C · Copa do Brasil · Copa Libertadores
```

```
$ python -m brazilian_soccer.cli call standings competition="Serie A" season=2019

2019 Brasileirão Série A standings (calculated from 380 matches):
1. Flamengo (RJ) - 90 pts (28W, 6D, 4L) 86:37 GD +49 - Champion
2. Santos (SP) - 74 pts (22W, 8D, 8L) 60:33 GD +27
3. Palmeiras (SP) - 74 pts (21W, 11D, 6L) 61:32 GD +29
...
17. Cruzeiro (MG) - 36 pts (7W, 15D, 16L) 27:46 GD -19 - Relegated
18. CSA (AL) - 32 pts (8W, 8D, 22L) 24:58 GD -34 - Relegated
19. Chapecoense (SC) - 32 pts (7W, 11D, 20L) 31:52 GD -21 - Relegated
20. Avaí (SC) - 20 pts (3W, 11D, 24L) 18:62 GD -44 - Relegated
```

Every one of those rows matches the real 2019 season — including Santos ahead of Palmeiras
on equal points, which the wins tie-break decides.

## Quick start

```bash
python -m venv venv && ./venv/bin/pip install -r requirements.txt

./venv/bin/python -m brazilian_soccer.server          # run the MCP server (stdio)
./venv/bin/python -m brazilian_soccer.cli demo        # answer 31 sample questions
./venv/bin/python -m brazilian_soccer.cli tools       # list the tools and arguments
./venv/bin/python -m pytest                           # 283 tests, ~7 seconds
```

Register it with an MCP client (Claude Desktop / Claude Code / any MCP host):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "brazilian_soccer.server"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

`--data-dir` (or `BRAZILIAN_SOCCER_DATA`) points the server at CSVs elsewhere.

## The 17 tools

| Area | Tools |
|------|-------|
| Discovery | `dataset_overview`, `search_teams` |
| Matches | `find_matches`, `head_to_head`, `biggest_wins`, `derbies` |
| Teams | `team_stats`, `team_profile`, `team_rankings` |
| Players | `search_players`, `player_profile`, `team_squad` |
| Competitions | `standings`, `knockout_bracket`, `competition_stats`, `compare_seasons` |
| Raw graph | `graph_neighbours` |

Every tool takes loose club names — `"Palmeiras-SP"`, `"Atletico Mineiro"`, `"Timão"`,
`"Fla"` all resolve — and returns text formatted the way the specification's example
answers are laid out. Failures come back as an explanation plus suggestions
(`"No team matching 'Manchester United'... Did you mean:"`) rather than as errors, so a
model can retry.

## How it works

```
data/kaggle/*.csv
      │
      ├─ names.py      entity resolution: accents, state suffixes, aliases, nicknames
      ├─ loaders.py    CSV parsing + cross-source de-duplication of fixtures
      ├─ models.py     Match / Player / TeamRecord
      ├─ graph.py      knowledge graph: nodes, relations, indexes, player↔club links
      ├─ queries.py    analytics: match search, tables, rankings, head-to-head
      ├─ formatting.py rendering for humans and LLMs
      ├─ server.py     the 17 MCP tools
      └─ cli.py        the same tools from a terminal
```

The graph is built lazily on the first tool call (~0.9 s for all six files) and then held
in memory, so every query afterwards is a dict lookup or a scan of at most 16,742 records:
simple lookups run in well under a millisecond, and the heaviest full-dataset aggregate is
~25 ms — against the specification's 2 s and 5 s budgets.

### Nodes and relations

Node ids are namespaced, and `graph_neighbours` walks them:

```
team:flamengo ──played_home──→ match:serie-a:2019:flamengo:santos ──part_of──→ competition:serie-a
      │                                     │                                        │
   based_in                             played_at                                in_season
      ↓                                     ↓                                        ↓
  state:RJ                        venue:Maracanã                              season:2019

player:158023 ──plays_for──→ team:santos      team:gremio ──squad──→ player:...
```

### Three problems worth calling out

**1. The same match appears in up to three files.** Brasileirão 2014–2019 is in
`Brasileirao_Matches.csv`, `novo_campeonato_brasileiro.csv` *and* `BR-Football-Dataset.csv`.
Loading them naively triples every league table. `merge_matches` groups candidates by
`(competition, season, home, away)` and fuses records that share a round number or fall
within three days of each other, keeping the richest value for each field — round from the
league file, stadium from the historical file, shots and corners from the stats file — and
recording provenance in `match.sources`. 23,954 rows become 16,742 matches.

Three edge cases the rule has to survive: postponed fixtures where sources disagree about
both the date *and* the round number (merged, they are one match); Botafogo hosting Flamengo
in **both** round 12 and round 31 of 2009 (kept apart, they are two); and Série C, which is
only covered by the file without round numbers and where a pairing legitimately repeats in a
second phase (so two records from the *same* file only merge when they are days apart).

**2. Every file spells clubs differently.** `"Palmeiras-SP"`, `"Palmeiras - SP"`,
`"Palmeiras"`; `"Sport-PE"` vs `"Sport Club do Recife"`; `"Atlético-MG"` vs
`"Atletico Mineiro"`; `"América FC (Minas Gerais)"` in the FIFA file. Resolution strips
accents, splits off state/country codes (`-SP`, ` - RJ`, `(URU)`, ` MG`), joins dotted
acronyms (`"A.b.c."` → `abc`), drops club-type words (`FC`, `Esporte Clube`, `Sport Club`)
and then consults a curated registry of 358 clubs with aliases and nicknames.

Clubs that merely *share* a name never collapse: Botafogo-RJ/PB/SP, Vitória-BA/ES,
Santos-SP/AP, Nacional of Uruguay/Paraguay/Amazonas and Peñarol of Uruguay/Amazonas all
stay distinct, and an unregistered state produces its own `base-uf` id rather than joining
the wrong club.

**3. The data has errors.** `novo_campeonato_brasileiro.csv` files Vitória (Bahia) under
`Mandante_UF = "ES"` and Bahia under `"BH"`, so the name is trusted over the state column.
`BR-Football-Dataset.csv` has no season column and the COVID-hit 2020 season ran into
February 2021, so league matches played in January–March are attributed to the previous
season; that same file labels one Campeonato Brasiliense match as Série A, which is why
league tables drop teams with implausibly few matches — and say so in a note.
`Brazilian_Cup_Matches.csv` names *both* sides of two 2019 fixtures "Bragantino - PA", so
matches where a club plays itself are dropped rather than counted as wins on both sides.
And where the sources disagree about a postponed fixture's date, the record that carries
the result wins: an unplayed row's date is a schedule, not a fact.

### Calculated, not looked up

The datasets contain match results and FIFA attributes, nothing else. So:

* **League tables** are computed from results, ordered the way the CBF does it: points,
  then **wins**, then goal difference, then goals scored. Wins matter — that criterion puts
  Santos above Palmeiras on 74 points in 2019 and decides who went down in Série B 2017.
  Champions and relegation are only asserted when every club in the table has played a full
  season; 2023 is truncated in the source and is reported as such.
* **Cup stages** are derived. The Copa do Brasil file only numbers its rounds, so stage
  names are inferred by walking backwards from the last round (2 matches = two-legged
  final, 4 = semi-finals, and each earlier round must double). This keeps the two-match
  *opening* rounds of 2013–2015 from being mistaken for finals, and correctly leaves the
  truncated 2021 season ending at the round of 16.
* **Knockout winners** come from the two-leg aggregate. A tie that finishes level is
  reported as undecided, with the away-goals split shown for context — applying the away
  goals rule would be wrong, as the 2015 Copa do Brasil final proves: 2-2 with Santos ahead
  on away goals, and Palmeiras won it on penalties, which no file records.
* **Top scorers cannot be derived** — there is no goalscorer, card or lineup data anywhere
  in the six files. The tools say so and offer top-scoring *teams* instead.

A useful check on all of the above: the champion and the four relegated clubs computed for
every Série A season from 2003 to 2022 match the real historical record exactly — Cruzeiro
2003 through Palmeiras 2022, including Corinthians' relegation in 2007 and Internacional's
in 2016. A single duplicated fixture or a split club node would move those tables.

### Joining players to matches

`fifa_data.csv` (a FIFA 19 snapshot) is linked to the match graph through the same name
resolver, but a link is only kept when the club's squad is majority Brazilian. That is what
stops FIFA's `"Inter"` (Internazionale) being wired to Internacional of Porto Alegre and
`"Boavista FC"` (Portugal) to Boavista of Rio. Fifteen clubs link — Grêmio, Santos,
Cruzeiro, Atlético Mineiro, Athletico Paranaense, Internacional, Fluminense, Botafogo,
Bahia, Vitória, Ceará, Chapecoense, Sport Recife, Paraná and América-MG — and
`team_squad` returns their FIFA squad next to their match record.

Flamengo, Palmeiras, Corinthians, São Paulo and Vasco are *not* in that FIFA snapshot; asking
for their squad says so and lists the clubs that are, rather than returning nothing.

## Testing

283 tests, all Given/When/Then, each carrying the scenario it implements in its docstring:

```gherkin
Feature: Match Queries

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
```

```python
def test_given_two_teams_when_searching_then_every_match_is_described(self, graph):
    result = queries.find_matches(graph, team="Flamengo", opponent="Fluminense", limit=50)

    assert result["total"] > 30
    assert result["derby"] == "Fla-Flu"
    for match in result["matches"]:
        assert match["date"]
        assert match["home_goals"] is not None and match["away_goals"] is not None
        assert match["competition"]
```

| File | Covers |
|------|--------|
| `test_names.py` | Name resolution, ambiguity, registry round-trip, competitions |
| `test_loaders.py` | All six CSVs, date/score formats, de-duplication, derived stages |
| `test_graph.py` | Nodes, every relation kind, FIFA↔match club linking |
| `test_queries_matches.py` | Match search, head-to-head, derbies, aggregates |
| `test_queries_teams.py` | Team records, profiles, rankings |
| `test_queries_players.py` | Player search/profile, cross-file squad joins |
| `test_queries_competitions.py` | Standings vs. the historical record, brackets |
| `test_formatting.py` | Output layouts, partial data, error rendering |
| `test_server.py` | Tool surface, schemas, every tool called, entry point |
| `test_demo.py` | All 31 specification sample questions, end to end |
| `test_performance.py` | The 2 s / 5 s budgets |
| `test_cli.py` | Terminal client |

```bash
./venv/bin/python -m pytest                      # everything
./venv/bin/python -m pytest -m performance       # just the timing budgets
./venv/bin/python -m pytest --cov=brazilian_soccer --cov-report=term-missing   # 93%
```

## Specification checklist

| Requirement | Status |
|---|---|
| Search matches from all provided CSVs | `find_matches` over all five match files, de-duplicated |
| Search player data | `search_players`, `player_profile` over 18,207 FIFA players |
| Calculate statistics (wins, losses, goals) | `team_stats`, `team_rankings`, `competition_stats` |
| Compare teams head-to-head | `head_to_head`, with per-competition breakdown and derby names |
| Handle team name variations | 725 raw spellings unified into 363 club nodes; `search_teams` shows the mapping |
| Properly formatted responses | Formatters follow the specification's answer layouts |
| Simple lookups < 2 s | Sub-millisecond after a ~0.9 s lazy load |
| Aggregate queries < 5 s | Heaviest full-dataset aggregate ≈ 25 ms |
| No timeout errors | 50 consecutive queries complete in well under one budget |
| All 6 CSV files loadable and queryable | Asserted in `test_loaders.py` |
| At least 20 sample questions | 31, in `brazilian_soccer/demo.py`, all asserted |
| Cross-file queries work | `team_squad` and `team_profile` join FIFA players to match records |

## Data

Pre-downloaded in `data/kaggle/` (see [TASK.md](TASK.md) for the schemas):

| File | Rows | Source | Licence |
|------|------|--------|---------|
| `Brasileirao_Matches.csv` | 4,180 | [ricardomattos05](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | 1,337 | same | CC BY 4.0 |
| `Libertadores_Matches.csv` | 1,255 | same | CC BY 4.0 |
| `BR-Football-Dataset.csv` | 10,296 | [cuecacuela](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 |
| `novo_campeonato_brasileiro.csv` | 6,886 | [macedojleo](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | 18,207 | [youssefelbadry10](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

Demo / non-commercial use, per the specification.
