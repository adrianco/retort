# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
provides a knowledge-graph–style query interface over six bundled Brazilian
soccer datasets. It lets an LLM answer natural-language questions about
players, teams, matches, and competitions by calling structured tools.

Implemented in pure Python (standard library only at runtime, plus the official
`mcp` SDK) against the spec in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
/ [`TASK.md`](TASK.md).

---

## What was built

| Layer | File | Responsibility |
|-------|------|----------------|
| Normalization | `brazilian_soccer_mcp/normalize.py` | Canonicalize inconsistent team names (state suffixes, accents, country codes, club-type tokens, official long names) into a stable key + clean display name. |
| Data loading | `brazilian_soccer_mcp/data_loader.py` | Parse all 6 CSVs into one normalized in-memory model; handle multiple date formats; **deduplicate** the same fixture appearing across overlapping datasets. |
| Query engine | `brazilian_soccer_mcp/queries.py` | Pure functions for every required capability; return JSON-serializable dicts. |
| MCP server | `brazilian_soccer_mcp/server.py` | Expose 15 query tools over stdio via `FastMCP`. |
| Demo | `demo.py` | Answer sample questions without an MCP client. |
| Tests | `tests/` | BDD (Gherkin) scenarios + GWT unit tests. |

### Capabilities (all from the spec)

1. **Match queries** — `find_matches` (by team / competition / season / date range / venue), `head_to_head`.
2. **Team queries** — `team_record`, `team_summary`, `compare_teams` (with home/away splits and per-competition breakdowns).
3. **Player queries** — `find_players`, `get_player`, `club_squad` (search by name / nationality / club / position / rating).
4. **Competition queries** — `standings` (computed from results, 3/1/0 points), `season_results`, `list_competitions`.
5. **Statistical analysis** — `competition_stats` (avg goals, home/away/draw rates), `biggest_wins`, `best_records`, `top_scoring_teams`.

---

## Data handling highlights

The six datasets overlap heavily and use inconsistent conventions; the loader
reconciles them so aggregates are correct:

- **Team-name normalization.** `"Palmeiras-SP"`, `"São Paulo"`, `"EC Bahia"`,
  `"Fortaleza FC"`, `"Athletico"` and `"Atlético Paranaense"` all resolve to the
  right canonical club — while genuinely distinct clubs that share a base name
  (`Atlético-MG` vs `Atlético-GO` vs `Athletico-PR`) are kept separate via a
  state-aware key plus a curated alias map.
- **Deduplication.** Season 2019 Série A appears in *three* files
  (`Brasileirao_Matches`, `novo_campeonato_brasileiro`, and the Serie A rows of
  `BR-Football-Dataset`). Fixtures are keyed by `(competition, season, home,
  away)` — robust to the ±1-day kick-off date offsets between sources — so each
  real match is counted once, and extended stats from `BR-Football` are merged
  into the kept record.
- **Multiple date formats** (`2023-09-24`, `2012-05-19 18:30:00`, `29/03/2003`)
  and **UTF-8** Portuguese text are handled throughout.

Validation of the computed standings against history: 2010 → Fluminense,
2015 → Corinthians, 2019 → Flamengo, 2021 → Atlético Mineiro (all correct),
and the average goals/match for the Brasileirão is ~2.47, matching the spec.

> Note: cross-source reconciliation is best-effort. A few sparsely-named teams
> in some seasons (notably 2021) retain minor duplication, and the bundled 2019
> FIFA dataset does not include every Brazilian club (e.g. Flamengo).

---

## Installation

Requires **Python ≥ 3.10** (the MCP SDK does not support 3.9).

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .            # runtime (mcp)
pip install -e '.[test]'    # + pytest, pytest-bdd for the test suite
```

---

## Running the MCP server

```bash
bsoccer-mcp                 # console script (stdio transport)
# or
python -m brazilian_soccer_mcp.server
```

Example MCP client configuration (e.g. Claude Desktop `mcpServers`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "bsoccer-mcp"
    }
  }
}
```

### Try it without a client

```bash
python demo.py
```

---

## Example questions it answers

| Question | Tool call |
|----------|-----------|
| "Show all Flamengo vs Fluminense matches" | `head_to_head("Flamengo", "Fluminense")` |
| "What matches did Palmeiras play in 2019?" | `find_matches(team="Palmeiras", season=2019)` |
| "Corinthians' home record in 2022?" | `team_record("Corinthians", season=2022, venue="home")` |
| "Who are the top Brazilian players?" | `find_players(nationality="Brazil")` |
| "Who is Casemiro?" | `get_player("Casemiro")` |
| "Who won the 2019 Brasileirão?" | `standings(2019)` |
| "Average goals per match in the Brasileirão?" | `competition_stats(competition="Brasileirão Série A")` |
| "Biggest wins in the Libertadores?" | `biggest_wins(competition="Libertadores")` |
| "Which team has the best home record?" | `best_records(venue="home", season=2019)` |

---

## Testing (BDD + GWT)

Behavior is specified as Gherkin features in `tests/features/` (one per
capability area) with pytest-bdd step definitions, complemented by
Given-When-Then unit tests in `tests/test_unit.py`.

```bash
pytest -q
# 52 passed
```

The suite covers 20+ sample questions, normalization edge cases, date parsing,
and the live MCP tool layer (tool registration + JSON-RPC invocation).

### Performance

All queries run in-memory after a ~0.3s one-time CSV load:

- Simple lookups: < 10 ms
- Aggregate queries (standings, rankings): < 5 ms

Comfortably within the spec's < 2 s / < 5 s targets.

---

## Project layout

```
brazilian_soccer_mcp/
├── __init__.py
├── normalize.py      # team-name canonicalization
├── data_loader.py    # CSV ingestion, normalized model, dedup
├── queries.py        # query engine (all capabilities)
└── server.py         # MCP server (15 tools, stdio)
tests/
├── conftest.py
├── features/*.feature           # Gherkin BDD scenarios
├── test_*_bdd.py                # pytest-bdd step definitions
└── test_unit.py                 # GWT unit + MCP-layer tests
demo.py                          # standalone demo
pyproject.toml / requirements.txt
data/kaggle/*.csv                # provided datasets
```

---

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets were pre-downloaded into `data/kaggle/`:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
  — License: CC BY 4.0
  - `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
  — License: CC0 Public Domain
  - `BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
  — License: CC BY 4.0
  - `novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
  — License: Apache 2.0
  - `fifa_data.csv`

## Specification

See [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).
