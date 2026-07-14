# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server that exposes a knowledge graph
over six pre-downloaded Kaggle datasets of Brazilian soccer, so an LLM can answer
natural-language questions about players, teams, matches, competitions and
aggregated statistics. Implementation of the specification in
[`TASK.md`](TASK.md) / [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## What was built

A pure-Python (3.10+) package, `brazilian_soccer/`, with four layers:

| Module | Responsibility |
|--------|----------------|
| `data_loader.py` | Load & normalise the six CSVs into typed `Match` / `Player` records. Handles team-name variations, multiple date formats, UTF-8, and cross-file deduplication. |
| `knowledge_graph.py` | In-memory knowledge graph linking teams → matches → competitions and teams → players, with O(1) lookup indexes. |
| `queries.py` | The query engine implementing all five capability areas, plus human-readable formatters. |
| `server.py` | A FastMCP server exposing 15 tools over the MCP protocol. |
| `cli.py` | A small command-line front-end for manual exploration / demos. |

The knowledge graph is held **in memory** (plain objects + dict indexes), so
there is no external database to run. It builds in ~0.5 s and answers simple
lookups in well under the 2 s budget and aggregate queries under 5 s.

### Data reconciliation (the interesting part)

The datasets overlap and disagree on naming, which is handled explicitly:

- **Team-name normalisation** — `"Palmeiras-SP"`, `"Palmeiras"` and `"PALMEIRAS"`
  all map to the key `palmeiras` (state suffixes, parentheticals like
  `"Nacional (URU)"` and accents are folded). The handful of base names shared by
  distinct clubs (Atlético-**MG**/**PR**/**GO**, América, Botafogo) keep their
  state so they are **not** wrongly merged.
- **Date formats** — ISO (`2023-09-24`), Brazilian (`29/03/2003`) and timestamped
  (`2012-05-19 18:30:00`) are all parsed.
- **Cross-file duplication** — the same season often appears in two or three
  files (e.g. the 2003-2019 Brasileirão), each spelling teams differently. For
  each `(competition, season)` we keep a single authoritative source (the one
  with the most fixtures, league files preferred). This is what makes computed
  standings exact — e.g. **2019 Brasileirão: Flamengo 90 pts (28W 6D 4L)**,
  matching the real final table.

## MCP tools

| Area | Tools |
|------|-------|
| Match | `find_matches`, `matches_between` |
| Team | `team_record`, `compare_teams` |
| Player | `search_players`, `players_by_nationality_clubs` |
| Competition | `standings`, `champion`, `relegated`, `list_competitions` |
| Statistics | `head_to_head`, `competition_stats`, `biggest_wins`, `best_record`, `top_scoring_teams` |

Each tool returns structured JSON; tools whose spec shows an example answer also
include a formatted `text` field.

## Setup

Requires **Python ≥ 3.10** (the `mcp` SDK constraint).

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the MCP server

```bash
python -m brazilian_soccer.server      # stdio transport
```

Register it with an MCP client (e.g. Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "brazilian_soccer.server"],
      "env": { "BR_SOCCER_DATA_DIR": "/absolute/path/to/data/kaggle" }
    }
  }
}
```

(`BR_SOCCER_DATA_DIR` is optional; it defaults to the bundled `data/kaggle/`.)

## Trying it without an MCP client (CLI)

```bash
python -m brazilian_soccer.cli matches  --team Flamengo --opponent Fluminense
python -m brazilian_soccer.cli record    --team Corinthians --season 2022 --venue home
python -m brazilian_soccer.cli standings --competition "Brasileirão Série A" --season 2019
python -m brazilian_soccer.cli players   --nationality Brazil --limit 10
python -m brazilian_soccer.cli stats     --competition "Brasileirão Série A"
python -m brazilian_soccer.cli h2h       --team-a Palmeiras --team-b Santos
```

## Tests

BDD (Given-When-Then) scenarios with `pytest-bdd` plus unit / integration and
sample-question tests:

```bash
pytest
```

```
tests/
  features/                 # Gherkin .feature files (BDD scenarios)
  test_bdd_steps.py         # GWT step definitions
  test_unit.py              # normalisation, dates, stats, performance budgets, MCP registration
  test_sample_questions.py  # 25 spec sample questions, each asserted answerable
```

All 62 tests pass and cover every item in the specification's success criteria:
all six CSVs loadable and queryable, 25 ≥ 20 sample questions answered,
head-to-head and standings correctness, name-variation handling, and the
performance budgets.

## Data sources & licenses

Pre-downloaded under `data/kaggle/` (Kaggle requires an account to download):

| File | Source | License |
|------|--------|---------|
| `Brasileirao_Matches.csv` | [ricardomattos05/jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | same | CC BY 4.0 |
| `Libertadores_Matches.csv` | same | CC BY 4.0 |
| `BR-Football-Dataset.csv` | [cuecacuela/brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 Public Domain |
| `novo_campeonato_brasileiro.csv` | [macedojleo/campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | [youssefelbadry10/fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

## Task tracking

Subtasks were tracked with [`bd`](https://github.com/) (beads): data loader,
knowledge graph, query engine, MCP server, BDD tests, and docs — all closed.
