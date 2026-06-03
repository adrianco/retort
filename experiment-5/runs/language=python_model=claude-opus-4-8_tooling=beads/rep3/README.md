# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
exposes a **knowledge-graph query interface** over Brazilian soccer data —
matches, teams, players, competitions and statistics — so an LLM can answer
natural-language questions like *"Who won the 2019 Brasileirão?"* or *"Compare
Palmeiras and Santos head-to-head."*

Built against the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) /
[`TASK.md`](TASK.md).

---

## What was implemented

| Layer | Module | Responsibility |
|-------|--------|----------------|
| **Normalization** | `brazilian_soccer/normalization.py` | Collapse the many surface forms of each team name onto a canonical key (handles state suffixes, accents, full legal names, `Athletico`↔`Atletico` spelling) **without** merging genuinely different clubs (Atlético-MG/PR/GO, América-MG/RN). |
| **Models** | `brazilian_soccer/models.py` | Dependency-free `Match` / `Player` dataclasses with pre-computed normalized keys. |
| **Data loader** | `brazilian_soccer/data_loader.py` | Parse all six CSV files (multiple date formats, UTF-8/BOM), tag each match with a canonical competition + a de-duplication `primary` flag. |
| **Knowledge graph** | `brazilian_soccer/knowledge_graph.py` | In-memory property graph (Team↔Match↔Player) with inverted indexes by team, competition, season, club and nationality. Loaded once, shared by every query. |
| **Query layer** | `brazilian_soccer/queries.py` | Pure, side-effect-free functions implementing all five spec capability areas. Shared by both the server and the tests. |
| **MCP server** | `brazilian_soccer/server.py` | `FastMCP` server exposing 15 tools over stdio. |
| **Tests** | `tests/` + `conftest.py` | 52 BDD (Given-When-Then) pytest tests. |

> **Design note — knowledge graph vs Neo4j.** The graph is built entirely in
> Python (stdlib only) rather than requiring an external Neo4j server, so the
> project runs and tests with zero infrastructure. It models the same
> Team→PLAYED→Match→TEAM and Player→PLAYS_FOR→Team relationships via indexes.

### MCP tools exposed

```
Match        find_matches · head_to_head · last_meeting
Team         team_record · compare_teams
Player       search_players · top_players · brazilian_players_by_club
Competition  standings · list_competitions
Statistics   competition_stats · biggest_wins · best_home_record · best_away_record
Introspect   dataset_summary
```

---

## Data handling highlights

* **Team name normalization** — `Flamengo-RJ`, `Flamengo` and
  `Sport Club Corinthians Paulista` resolve correctly; ambiguous bases keep
  their state suffix so the three *Atléticos* stay distinct.
* **Multiple date formats** — ISO (`2023-09-24`), Brazilian (`29/03/2003`) and
  datetime (`2012-05-19 18:30:00`) are all parsed.
* **De-duplication** — the Brasileirão appears in three overlapping files. Each
  match carries a `primary` flag so standings/aggregates use exactly one source
  per `(competition, season)`:
  * Brasileirão 2003–2011 → `novo_campeonato_brasileiro.csv`
  * Brasileirão 2012–2022 → `Brasileirao_Matches.csv`
  * Copa do Brasil → `Brazilian_Cup_Matches.csv`, Libertadores →
    `Libertadores_Matches.csv`, Série B/C → `BR-Football-Dataset.csv`
* **Incomplete seasons** — records count only *completed* (scored) matches; the
  provided 2022 set is a mid-season snapshot.

Verified against a known real result: the computed **2019 Brasileirão**
standings reproduce Flamengo as champions on **90 pts (28W-6D-4L)**, exactly as
in the specification.

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # or: pip install -e ".[test]"
```

## Running the MCP server

```bash
python -m brazilian_soccer.server      # serves over stdio
```

### Register with an MCP client (e.g. Claude Desktop)

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["-m", "brazilian_soccer.server"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

## Using the query layer directly

```python
from brazilian_soccer.knowledge_graph import get_graph
from brazilian_soccer import queries as q

g = get_graph()
print(q.standings(g, "Brasileirão", 2019)["summary"][0])
# 1. Flamengo - 90 pts (28W, 6D, 4L) - Champion

print(q.head_to_head(g, "Flamengo", "Fluminense")["summary"])
print(q.top_players(g, nationality="Brazil", limit=3)["summary"])
```

## Running the tests

```bash
pytest -q          # 52 BDD tests, ~2s
```

The suite is written in **BDD Given-When-Then** style and covers every spec
capability area, the performance budget (< 2s simple / < 5s aggregate), 20+
sample questions, cross-file (player + match) queries, and the team-name
normalization edge cases.

---

## Task tracking

Work was tracked with [beads](https://github.com/) (`bd`): the build was split
into data-layer, query-layer, MCP-server, test-suite and docs issues, each
claimed and closed in turn (`bd list` to view).

---

## Data Sources

Kaggle data can't be downloaded without an account, so these freely-available
(with attribution) datasets are included under `data/kaggle/`:

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
