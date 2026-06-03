# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
provides a knowledge-graph interface over six Brazilian-soccer datasets. It lets
an LLM client answer natural-language questions about matches, teams, players,
competitions and aggregate statistics.

Built to the specification in [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md)
(also mirrored in `TASK.md`).

## What was built

```
soccer_mcp/
├── __init__.py          # package context + public exports
├── models.py            # Match / Player dataclasses (typed records)
├── normalize.py         # team-name, accent and date normalisation
├── data_loader.py       # parses the 6 CSV files + cross-source dedup
├── knowledge_graph.py   # in-memory store + the full query API
├── formatting.py        # renders results as human-readable answers
└── server.py            # FastMCP server exposing the query API as tools
tests/                   # BDD (Given/When/Then) pytest suite (62 tests)
demo.py                  # answers 20+ sample questions without an MCP client
```

Every source file starts with a **context block comment** describing its role.

### Architecture

The data and query layers are completely independent of the MCP transport, so
the logic is unit-testable without a running server and **without any external
database**. `server.py` is a thin adapter that loads the knowledge graph once
and exposes each query as an MCP tool.

> **On Neo4j:** the spec mentions a graph database as an option. The data
> (~17k deduplicated matches, ~18k players) fits trivially in memory, so we
> model the same entities and relationships — teams, matches and players as
> nodes; *played*, *plays_for* and *competed_in* as edges — using plain Python
> indexes in `knowledge_graph.py`. This keeps the test-suite hermetic (no server
> to stand up) while preserving graph-style traversal queries.

### Data handling highlights

- **Team-name normalisation** — strips state suffixes (`Palmeiras-SP`), country
  codes (`Nacional (URU)`), folds accents (`Grêmio` → `gremio`) and resolves
  long official names (`Sport Club Corinthians Paulista` → `corinthians`).
- **Multiple date formats** — ISO (`2012-05-19 18:30:00`) and Brazilian
  (`29/03/2003`) are parsed to a single ISO `YYYY-MM-DD` form.
- **UTF-8** throughout, with BOM tolerance for `fifa_data.csv`.
- **Cross-source deduplication** — the three Brasileirão files and the two Copa
  do Brasil files overlap on shared seasons. For each `(competition, season)` we
  keep a single canonical source, so a computed league table counts each match
  once. This reproduces the spec's example exactly: **2019 Brasileirão champion
  Flamengo, 90 pts (28W 6D 4L)**.

## Datasets

All data lives in `data/kaggle/` (see licenses below):

| File | Rows | Content |
|------|------|---------|
| `Brasileirao_Matches.csv` | 4,180 | Brasileirão Série A 2012–2022 |
| `Brazilian_Cup_Matches.csv` | 1,337 | Copa do Brasil 2012–2021 |
| `Libertadores_Matches.csv` | 1,255 | Copa Libertadores 2013–2022 |
| `BR-Football-Dataset.csv` | 10,296 | Multi-competition + extended stats |
| `novo_campeonato_brasileiro.csv` | 6,886 | Historical Brasileirão 2003–2019 |
| `fifa_data.csv` | 18,207 | FIFA player database |

### Data sources & licenses

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — CC BY 4.0 (`Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`)
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — CC0 Public Domain (`BR-Football-Dataset.csv`)
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — CC BY 4.0 (`novo_campeonato_brasileiro.csv`)
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — Apache 2.0 (`fifa_data.csv`)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the server

The server speaks MCP over **stdio** (the standard local-server transport):

```bash
python -m soccer_mcp.server
```

### Claude Desktop configuration

Add to `claude_desktop_config.json` (adjust paths):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "soccer_mcp.server"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

The dataset location can be overridden with the `SOCCER_DATA_DIR` env var.

## MCP tools

| Tool | Answers questions like |
|------|------------------------|
| `find_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2019?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_stats` | "What is Corinthians' home record in 2019?" |
| `find_players` | "Find all Brazilian players", "Show me forwards with overall ≥ 88" |
| `player_club_summary` | "Brazilian players grouped by club" |
| `standings` | "Show the 2019 Brasileirão final standings" |
| `league_champion` | "Who won the 2019 Brasileirão?" |
| `statistics` | "What's the average goals per match in the Brasileirão?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `top_scoring_teams` | "Which team scored the most goals in 2019?" |
| `list_competitions` | "What data is available?" |

## Demo

See answers to 20+ sample questions immediately, without an MCP client:

```bash
python demo.py
```

## Tests

BDD (Given/When/Then) scenarios with pytest, covering normalisation, data
loading + deduplication, and all five query categories plus the server layer:

```bash
python -m pytest
```

```
62 passed
```

The suite encodes the spec's Gherkin scenarios (e.g. *"Find matches between two
teams"*, *"Get team statistics"*) and asserts against known-correct facts such
as the 2019 Brasileirão final table.
