# Brazilian Soccer MCP Server

An **MCP (Model Context Protocol) server** that exposes a knowledge-graph style
interface over a collection of Brazilian soccer datasets, so an LLM can answer
natural-language questions about players, teams, matches, competitions and
statistics. Implements the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

---

## What was built

| Layer | File | Responsibility |
|-------|------|----------------|
| Normalisation | `brazilian_soccer_mcp/normalize.py` | Canonicalise team names, parse dates, strip accents |
| Data loading | `brazilian_soccer_mcp/data_loader.py` | Load & unify the 6 CSVs into tidy `matches` / `players` tables |
| Query engine | `brazilian_soccer_mcp/knowledge_graph.py` | All query logic (the in-memory knowledge graph) |
| Formatting | `brazilian_soccer_mcp/formatting.py` | Render results as human-readable text |
| MCP server | `brazilian_soccer_mcp/server.py` | Expose the engine as MCP tools (FastMCP, stdio) |

The architecture is layered on purpose: **all business logic lives in the query
engine and is pure Python data in / data out**, so it is fully unit-testable
without a running server or external database. The MCP server is a thin adapter.

### Why in-memory (pandas) instead of Neo4j?

The spec lists a graph database as one option. This implementation uses an
**in-memory knowledge graph built on pandas** so the deliverable is completely
self-contained — it needs no running database, starts instantly, and lets the
full BDD test-suite run anywhere. Matches load in ~0.7s and every query returns
in well under the spec's 2s/5s latency budgets.

---

## Data handling highlights

The six datasets use inconsistent conventions; the loader reconciles them:

* **Team-name canonicalisation.** `Atletico-MG`, `Atletico Mineiro` resolve to
  the *same* club, while the three distinct Atléticos (MG / PR / GO) and the two
  Américas stay **separate**. State suffixes (`-SP`), country codes
  (`Nacional (URU)`) and org words (`EC Bahia`) are handled. Accents and UTF-8
  are preserved for display but ignored for matching.
* **Multiple date formats** — ISO, ISO+time and Brazilian `DD/MM/YYYY`.
* **Overlap de-duplication.** Série A appears in three files. For each
  `(competition, season)` the loader keeps only the single most authoritative
  source, so standings and records are **not double-counted**. Verified against
  ground truth: the 2019 Brasileirão table reproduces Flamengo as champions with
  90 pts (28W-6D-4L) and the correct four relegated clubs.

### Datasets (bundled under `data/kaggle/`)

| File | Rows | Competition | License |
|------|------|-------------|---------|
| `Brasileirao_Matches.csv` | 4,180 | Brasileirão Série A (2012–2022) | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | 1,337 | Copa do Brasil | CC BY 4.0 |
| `Libertadores_Matches.csv` | 1,255 | Copa Libertadores | CC BY 4.0 |
| `BR-Football-Dataset.csv` | 10,296 | Série A/B/C + Copa do Brasil (extended stats) | CC0 |
| `novo_campeonato_brasileiro.csv` | 6,886 | Brasileirão Série A (2003–2019) | CC BY 4.0 |
| `fifa_data.csv` | 18,207 | FIFA player database | Apache 2.0 |

> Note: the FIFA-19 player dataset only licensed a subset of Brazilian clubs
> (e.g. Internacional, Grêmio, Santos, Cruzeiro are present; Flamengo, Palmeiras
> and Corinthians are not). Club-based player queries reflect that coverage.

---

## MCP tools

| Tool | Capability |
|------|-----------|
| `find_matches` | Matches by team / opponent / competition / season / date range |
| `last_meeting` | Most recent match between two teams |
| `team_record` | W/D/L, goals, win-rate (overall / home / away) |
| `head_to_head` | Head-to-head record & match list |
| `search_players` | Players by name / nationality / club / position / rating |
| `standings` | League table computed from results (3pts win / 1pt draw) |
| `champion` | Season champion |
| `relegated` | Relegation-zone teams |
| `competition_statistics` | Avg goals/match, home/away/draw rates |
| `biggest_wins` | Largest-margin matches |
| `best_record` | Teams ranked by home/away win rate |
| `list_competitions`, `list_seasons` | Discovery helpers |

---

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # pandas, mcp, pytest
# or:  pip install -e .
```

## Running the server

```bash
python run_server.py
# or
python -m brazilian_soccer_mcp.server
```

The server speaks MCP over **stdio**. Example client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["run_server.py"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

### Using the engine directly (no server)

```python
from brazilian_soccer_mcp import get_knowledge_graph

kg = get_knowledge_graph()
print(kg.champion("Brasileirão Série A", 2019))          # -> Flamengo, 90 pts
print(kg.head_to_head("Flamengo", "Fluminense")["total"])
print(kg.search_players(nationality="Brazil", limit=5))
```

---

## Testing (BDD / Given-When-Then)

The suite in `tests/` is written in a Behaviour-Driven style — each test maps to
a Given-When-Then scenario (documented in
[`features/brazilian_soccer.feature`](features/brazilian_soccer.feature)) and
covers all five required capability categories plus 24 end-to-end sample
questions through the MCP tools.

```bash
pytest            # 67 passing
```

Coverage:

* `test_data_loading.py` — all 6 files load; normalisation & de-duplication
* `test_match_queries.py` — match search by every criterion
* `test_team_queries.py` — records, home/away splits, head-to-head symmetry
* `test_player_queries.py` — name / nationality / club / position / rating
* `test_competition_queries.py` — standings, champion, relegation (2019 truth)
* `test_statistics.py` — goal averages, win rates, biggest wins, best records
* `test_server_tools.py` — every MCP tool + 24 parametrised sample questions

---

## Project layout

```
brazilian_soccer_mcp/      # the package
  normalize.py             # name/date canonicalisation
  data_loader.py           # CSV -> unified tables
  knowledge_graph.py       # query engine
  formatting.py            # text rendering
  server.py                # FastMCP server
tests/                     # BDD pytest suite
features/                  # Gherkin feature documentation
data/kaggle/               # bundled datasets
run_server.py              # launcher
requirements.txt / pyproject.toml
```
