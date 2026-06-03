# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
exposes a queryable knowledge graph of Brazilian soccer data — players, teams,
matches, competitions and statistics — built from the bundled Kaggle datasets.
It lets an LLM client (e.g. Claude Desktop) answer natural-language questions
such as *"Who won the 2019 Brasileirão?"*, *"Compare Palmeiras and Santos
head-to-head"* or *"Who are the top-rated Brazilian players?"*.

The full requirements are in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
(mirrored in [`TASK.md`](TASK.md)).

## What was built

| File | Responsibility |
|------|----------------|
| `team_names.py` | Region-aware team-name normalization (accents, suffixes, spelling, aliases). |
| `data_loader.py` | Loads & unifies all six CSVs into typed `Match`/`Player` records; de-duplicates overlapping fixtures. |
| `knowledge_graph.py` | In-memory query engine: matches, teams, players, competitions, statistics. |
| `formatters.py` | Renders query results as the human-readable answers from the spec. |
| `server.py` | `FastMCP` server registering 12 tools over the query engine (stdio transport). |
| `demo.py` | CLI to explore the same queries without an MCP client. |
| `tests/` | BDD (Given-When-Then) pytest suite — 44 scenarios across all capability families. |

### Architecture

```
CSV datasets ──► data_loader ──► [Match] / [Player]
                                      │
                                      ▼
                              KnowledgeGraph  ◄── team_names (normalization)
                                      │
                        ┌─────────────┴──────────────┐
                        ▼                             ▼
                   formatters                     server.py
                  (text output)                (MCP tools / FastMCP)
```

The datasets are loaded once into memory at start-up, so every query is an
in-memory lookup that meets the spec's latency targets (simple lookups < 2 s,
aggregates < 5 s — in practice milliseconds after a ~2 s load).

### MCP tools

* **Match:** `find_matches`, `head_to_head`
* **Team:** `team_record`, `team_competitions`
* **Player:** `search_players`, `top_brazilian_players`, `brazilian_players_by_club`
* **Competition:** `league_standings`, `list_seasons`
* **Statistics:** `average_goals`, `biggest_wins`, `best_team_records`

## Data handling

The spec calls out several data-quality challenges; here is how each is handled:

* **Multiple date formats** (`2012-05-19 18:30:00`, `2023-09-24`, `29/03/2003`)
  — parsed uniformly to `datetime.date`.
* **Goals as quoted strings / floats** (`"2"`, `1.0`) — coerced to `int`.
* **UTF-8 / accents / BOM** — read with `utf-8-sig`; accents folded for matching.
* **Team-name variations** — every club is reduced to a `base` name + a `region`
  (state/country code). The region is part of a club's *identity*
  (`Atlético-MG` ≠ `Atlético-GO` ≠ `Athletico-PR`), so it is **preserved**, while
  accents and spelling are folded (`Grêmio-RS` = `Gremio-RS`, `Athletico-PR` =
  `Atletico-PR`). Missing/mislabelled states in the historical file are repaired
  from each club's dominant region.
* **Overlapping datasets** — the same fixture appears across multiple files
  (e.g. 2012–2019 Brasileirão lives in both `Brasileirao_Matches.csv` and the
  historical file). Matches are de-duplicated by
  `(competition, teams, season-or-date)` so standings and statistics are not
  double-counted. As a result the in-memory graph holds ~16,000 **unique**
  matches.

### A note on the BR-Football dataset

`BR-Football-Dataset.csv` provides extended statistics (corners, shots, attacks)
but uses state-code-free, internally-inconsistent club names. Its **Serie A**
and **Copa do Brasil** rows merely duplicate the dedicated, region-aware
competition files, so they are dropped to keep standings and head-to-head
records clean. Its **Serie B** and **Serie C** rows (which exist in no other
dataset) are kept, along with their extended statistics — so the file remains
fully loaded and queryable and demonstrates the statistics/lower-division
capabilities.

Computed standings were spot-checked against history and match the real final
tables (e.g. 2019: Flamengo 90 pts champions; 2003: Cruzeiro 100 pts).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

### As an MCP server (stdio)

```bash
python server.py
```

Register it with an MCP client. Example Claude Desktop entry
(`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

### As a CLI (no MCP client needed)

```bash
python demo.py                                   # scripted tour of sample queries
python demo.py standings Brasileirao 2019
python demo.py h2h Palmeiras Santos
python demo.py matches Flamengo --opponent Fluminense
python demo.py team Corinthians --season 2019 --competition Brasileirao
python demo.py top-brazilians 10
python demo.py avg-goals --competition Brasileirao
python demo.py biggest-wins --competition Brasileirao
```

## Testing

The test-suite uses Behaviour-Driven Development (Given-When-Then) scenarios:

```bash
python -m pytest
```

44 scenarios cover match queries, team records & head-to-head, player search,
competition standings, statistical analysis, data loading/normalization,
de-duplication, and the MCP tool layer — plus the spec's latency targets.

## Data Sources

Kaggle data can't be downloaded without an account, so these freely-available
(attribution) datasets were pre-downloaded into `data/kaggle/`:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/Brasileirao_Matches.csv`
- `data/kaggle/Brazilian_Cup_Matches.csv`
- `data/kaggle/Libertadores_Matches.csv`

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- `data/kaggle/BR-Football-Dataset.csv`

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank — Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/novo_campeonato_brasileiro.csv`

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- `data/kaggle/fifa_data.csv`
