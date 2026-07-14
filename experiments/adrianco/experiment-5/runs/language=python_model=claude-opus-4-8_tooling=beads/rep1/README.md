# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes
a queryable **knowledge graph** of Brazilian soccer (matches, teams, players,
competitions) so an LLM can answer natural-language questions from the provided
Kaggle datasets. Implemented per [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## What was built

| File | Responsibility |
|------|----------------|
| `normalize.py` | Canonicalises the many team-name conventions across files (state suffixes, country codes, accents, spelling and full-name variants) onto one key per club, with state-based disambiguation for shared base names (Atlético MG/PR/GO, América MG/RN, Botafogo, Internacional, Sport, Nacional). |
| `models.py` | `Match` and `Player` dataclasses + derived fields (winner, totals, summaries). |
| `data_loader.py` | Loads all six CSVs with the stdlib `csv` module, normalises dates to ISO, and **de-duplicates** fixtures that appear in multiple source files (enriching, never double-counting). |
| `knowledge_graph.py` | In-memory graph (team/player/competition/match adjacency indexes) + the query engine for the five required query families. |
| `mcp_server.py` | MCP server speaking newline-delimited **JSON-RPC 2.0 over stdio** (`initialize`, `tools/list`, `tools/call`, `ping`), exposing 12 tools. |
| `demo.py` | Answers 22 sample questions through the MCP tools. |
| `tests/` | 61 BDD (Given/When/Then) PyTest tests. |

> **No third-party runtime dependencies.** The build sandbox had no network
> access, so the server, engine and loader use only the Python standard library
> (`csv`, `json`, `unicodedata`, `dataclasses`). This also makes it trivial to
> run in air-gapped environments. (PyTest is the only dev dependency.)

## Quick start

```bash
# 1. Run the test suite (loads all data, ~0.5s)
python3 -m pytest -q

# 2. See 22 sample questions answered end-to-end
python3 demo.py

# 3. Run the MCP server (stdio JSON-RPC) for an MCP client
python3 mcp_server.py
```

To connect an MCP client (e.g. Claude Desktop), see
[`mcp_config.example.json`](mcp_config.example.json).

## MCP tools

| Tool | Purpose |
|------|---------|
| `find_matches` | Matches by team / opponent / competition / season / date range / venue. |
| `head_to_head` | Head-to-head record + recent meetings between two teams. |
| `team_record` | Win/draw/loss & goals record, filterable by season, competition, venue. |
| `compare_teams` | Head-to-head plus each team's record. |
| `find_players` | FIFA players by name, nationality, club, position, min rating. |
| `standings` | League table computed from results (3 pts win, 1 draw). |
| `average_goals` | Goals-per-match average + home/away/draw rates. |
| `biggest_wins` | Largest victories by goal margin. |
| `best_record` | Rank teams by win rate or points (all/home/away). |
| `list_teams` / `list_competitions` / `list_seasons` | Discovery helpers. |

## Data handling notes

- **Team name normalization.** `"Palmeiras-SP"`, `"Palmeiras"`, `"São Paulo"` /
  `"Sao Paulo FC"`, `"Athletico-PR"` / `"Atletico Paranaense"` all collapse
  correctly. Clubs sharing a base name keep their state (`atletico mg` ≠
  `atletico pr`). See `tests/test_normalization.py`.
- **De-duplication.** Série A appears in three source files (overlapping
  seasons). Fixtures are keyed by `(competition, season, home, away)`; the
  richest source wins and others enrich missing fields. Verified: 2019, 2020 and
  2022 Série A each resolve to exactly **380 matches / 20 teams**.
- **Season inference.** `BR-Football-Dataset.csv` lacks a season column; the
  Brazilian league runs Apr–Dec within one calendar year, but the COVID-hit 2020
  season spilled into Jan–Feb 2021, so Jan/Feb matches are attributed to the
  prior season.
- **Dates** are normalised to ISO `YYYY-MM-DD` from the three source formats.
- **Encoding** is UTF-8 throughout (BOM-aware for `fifa_data.csv`).

## Validated against real results

The engine's computed standings match history, e.g. **2019 Brasileirão:
Flamengo champions with 90 pts (28W 6D 4L)**, **2022: Palmeiras**. See
`tests/test_competition_queries.py`.

## Testing

61 PyTest tests in BDD Given/When/Then style across eight feature files
(normalization, data loading, match/team/player/competition queries, statistics,
MCP protocol). The suite asserts the spec's functional, performance (simple
lookups < 2s, aggregates < 5s) and data-coverage criteria.

```bash
python3 -m pytest -v
```

## Data sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets were pre-downloaded into `data/kaggle/`:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — CC BY 4.0
  - `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — CC0 Public Domain
  - `BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — CC BY 4.0
  - `novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — Apache 2.0
  - `fifa_data.csv`

> Note: the FIFA dataset (FIFA 19 vintage) only licenses some Brazilian clubs by
> name (Grêmio, Santos, Cruzeiro, Internacional, Atlético Mineiro, Botafogo,
> Fluminense, América-MG, Chapecoense, Bahia, …); unlicensed clubs such as
> Flamengo, Palmeiras and Corinthians are absent or anonymised in that file.
> Match data covers all clubs.
